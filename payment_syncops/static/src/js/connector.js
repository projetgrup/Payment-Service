/** @odoo-module alias=paylox.syncops.page **/
'use strict';

import core from 'web.core';
import rpc from 'web.rpc';
import Dialog from 'web.Dialog';
import framework from 'paylox.framework';
import systemPage from 'paylox.system.page';
import { format } from 'paylox.tools';

const qweb = core.qweb;
const _t = core._t;

systemPage.include({
    events: _.extend({}, systemPage.prototype.events, {
        'click .o_connector_partner_get': '_onClickConnectorPartnerGet',
        'click .o_connector_partner_reset': '_onClickConnectorPartnerReset',
        'click .o_connector_partner_ledger_date': '_onClickConnectorPartnerLedgerDate',
    }),

    xmlDependencies: (systemPage.prototype.xmlDependencies || []).concat(
        ['/payment_syncops/static/src/xml/connector.xml']
    ),

    init: function () {
        this._super.apply(this, arguments);
        const self = this;
        this.connector = {
            dateFormat: 'DD-MM-YYYY',
            format: {
                date: (date) => format.date(date, self.connector.dateFormat),
                currency: (amount, currency) => format.currency(amount, currency.position, currency.symbol, currency.decimal),
            },
            partner: {
                page: 1,
                pageSize: 5,
                search: '',
                list: [],
                flist: [],
                filter: false,
                getRows: () => self.connector.partner.filter && self.connector.partner.flist || self.connector.partner.list,
                lines: 'paylox.syncops.partner.list.line',
                $lines: () => $('.o_connector_partner_table tbody'),
            },
            ledger: {
                page: 1,
                pageSize: 10,
                list: [],
                getRows: () => self.connector.ledger.list,
                lines: 'paylox.syncops.partner.ledger.line',
                $lines: () => $('.o_connector_partner_ledger_table tbody'),
            }
        };
    },

    start: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            if ($('.o_connector_partner_ledger_date').length) {
                self._getConnectorPartnerLedgerList();
            }
        });
    },

    _showLoading: function() {
        $('.o_connector_partner_loading').addClass('show');
    },

    _hideLoading: function() {
        $('.o_connector_partner_loading').removeClass('show');
    },

    _onClickConnectorPartnerGet: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        framework.showLoading();
        if (!this.connector.partner.list.length) {
            const self = this;
            rpc.query({ route: '/my/payment/partners' }).then(function (partners) {
                self._getConnectorPartners(partners);
            });
        } else {
            this._getConnectorPartners(this.connector.partner.list);
        }
    },

    _getConnectorPartners: function (partners) {
        const partner = this.connector.partner;
        partner.list = partners;
        partner.flist = [];
        partner.filter = false;
        const self = this;
        const popup = new Dialog(this, {
            title: _t('Select a partner'),
            $content: qweb.render('paylox.syncops.partner.list', { partner }),
            dialogClass: 'o_connector_partner_table'
        });
        popup.opened(function() {
            self._renderConnectorPages('partner');
            $('.o_connector_pages').click(self._onClickConnectorPage.bind(self));

            $('.o_connector_partner_search').click(self._onClickConnectorPartnerSearch.bind(self));
            $('.o_connector_partner_query').keypress(self._onClickConnectorPartnerSearch.bind(self));
            $('.o_connector_partner_table tbody').click(function(ev) {
                const $el = $(ev.target);
                if ($el.prop('tagName') !== 'BUTTON') return;
                $('.o_connector_partner_select').prop({'disabled': 'disabled'}).addClass('disabled');
                rpc.query({
                    route: '/my/payment/partners/select',
                    params: {
                        vat: $el.attr('data-vat'),
                        ref: $el.attr('data-ref'),
                        company: $el.attr('data-company'),
                    },
                }).then(function (result) {
                    $el.prop({'disabled': 'disabled'}).addClass('disabled');
                    $('input#campaign').val($el.data('campaign') || '');
                    $('span[name=partner]').text($el.data('company'));
                    $('.o_connector_partner_balance').html(qweb.render('paylox.syncops.balance', {
                        balances: result.balances,
                        show_balance: result.show_balance,
                        show_ledger: result.show_ledger,
                        show_total: result.show_total,
                    }));
                    $('.o_connector_partner_reset').prop({'disabled': false}).removeClass('d-none').removeClass('disabled');
                    popup.destroy();
                }).guardedCatch(function () {
                    popup.destroy();
                });
            });
        });
        popup.open();
        framework.hideLoading();
    },

    _onClickConnectorPartnerSearch: function (ev) {
        if (ev.key && ev.key !== 'Enter') return;
        const query = $('.o_connector_partner_query').val();
        const partner = this.connector.partner;
        partner.search = query;
        if (query) {
            const self = this;
            self._showLoading();
            rpc.query({
                route: '/my/payment/partners',
                params: { search: query }
            }).then(function (partners) {
                partner.list = partners;
                partner.flist = [];
                partner.filter = false;
                self._renderConnectorPages('partner');
                self._hideLoading();
            }).guardedCatch(function (error) {
                self._hideLoading();
            });

            //let regex = new RegExp(query, 'i');
            //partners = partners.filter((p) => p.name.match(regex));
            //partner.flist = partners;
            //partner.filter = true;
            //this._renderConnectorPages('partner');
        } else {
            partner.list = [];
            partner.flist = [];
            partner.filter = false;
            this._renderConnectorPages('partner');
        }
    },

    _onClickConnectorPage: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const $el = $(ev.target);
        if ($el.prop('tagName') !== 'BUTTON') return;
        const page = parseInt($el.data('page'));
        const type = $el.data('type');
        this._renderConnectorPages(type, page);
    },

    _getConnectorPartnerLedgerList: function () {
        const self = this;
        const $date_start = $('#date_start');
        const $date_end = $('#date_end');
        const format = $('#date_start').data('date-format');
        framework.showLoading();
        rpc.query({
            route: '/my/payment/partners/ledger/list',
            params: {
                partner: self.partner.value,
                start: $date_start.val(),
                end: $date_end.val(),
                format: format,
            },
        }).then(function (result) {
            if (result.error) {
                self.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: result.error,
                });
            } else {
                const ledger = self.connector.ledger;
                ledger.dateFormat = format;
                ledger.list = result.ledgers;
                self._renderConnectorPages('ledger');
                $('.o_connector_pages').click(self._onClickConnectorPage.bind(self));
            }
            framework.hideLoading();
        }).guardedCatch(function () {
            self.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured.'),
            });
            const render = qweb.render('paylox.syncops.partner.ledger.line', {ledgers: []});
            $('.o_connector_partner_ledger_table tbody').html(render);
            framework.hideLoading();
        });
    },

    _onClickConnectorPartnerLedgerDate: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this._getConnectorPartnerLedgerList();
    },

    _getConnectorPages: function (connector) {
        const page = connector.page;
        const firstPages = [];
        const middlePages = [];
        const lastPages = [];

        let total = Math.ceil(connector.getRows().length / connector.pageSize) || 1;
        let lastLimit = total;
        let iterator = 0;

        for(let i=1; i<=3; i++) {
            firstPages.push(i);
            if (total === i) break;
        }

        let firstLimit = firstPages.at(-1);
        for(let i=1; i<=3; i++) {
            if (lastLimit === firstLimit) break;
            lastPages.unshift(lastLimit);
            lastLimit--;
        }

        if (total > 6) {
            if (page < 4) {
                for(let i=4; i<=lastLimit; i++) {
                    middlePages.push(i);
                    iterator++;
                    if (iterator === 3) break;
                }
            } else if (page > lastLimit){
                for(let i=lastLimit; i>=4; i--) {
                    middlePages.unshift(i);
                    iterator++;
                    if (iterator === 3) break;
                }
            } else {
                for(let i=-1; i<=1; i++) {
                    middlePages.push(page + i);
                }
            }

            if (middlePages[0] === 3) {
                middlePages.shift();
                if (!lastPages.includes(6)) middlePages.push(6);
            }
            if (middlePages.at(-1) === lastPages[0]) {
                middlePages.pop();
                if (!firstPages.includes(lastLimit - 2)) middlePages.unshift(lastLimit - 2);
            }

            if (middlePages[0] > 4) middlePages.unshift(0);
            if (middlePages.at(-1) < lastLimit) middlePages.push(0);
        }
        return firstPages.concat(middlePages.concat(lastPages));
    },

    _renderConnectorPages: function (type, page=1) {
        const connector = this.connector[type];
        connector.page = page;
        const pageSize = connector.pageSize || 5;
        const pages = this._getConnectorPages(connector);
        const buttons = qweb.render('paylox.syncops.pages', {pages: pages, page: page, type: type});
        $('.o_connector_pages').html(buttons);

        const firstLine = (page - 1) * pageSize;
        const lines = qweb.render(connector.lines, {
            rows: connector.getRows().slice(firstLine, firstLine + pageSize),
            format: this.connector.format,
        });
        connector.$lines().html(lines);
    },

    _onClickConnectorPartnerReset: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const $el = $(ev.currentTarget);
        $el.prop({'disabled': 'disabled'}).addClass('disabled');
        rpc.query({
            route: '/my/payment/partners/reset',
        }).then(function (result) {
            if (!result) return false;
            $('span#campaign').html(result.campaign || '');
            $('span[name=partner]').text(result.name);
            $('.o_connector_partner_balance').html(qweb.render('paylox.syncops.balance', {
                balances: result.balances,
                show_balance: result.show_balance,
                show_ledger: result.show_ledger,
                show_total: result.show_total,
            }));
            $el.addClass('d-none');
        });
    },
});
