odoo.define('payment_syncops.payment_page', function (require) {
"use strict";

let core = require('web.core');
let publicWidget = require('web.public.widget');
let rpc = require('web.rpc');
let dialog = require('web.Dialog');
var framework = require('payment_jetcheckout.framework');
let paymentSystemPage = publicWidget.registry.JetcheckoutPaymentSystemPage;

let qweb = core.qweb;
let _t = core._t;

paymentSystemPage.include({
    events: _.extend({}, paymentSystemPage.prototype.events, {
        'click .o_connector_partner_get': '_onClickConnectorPartnerGet',
        'click .o_connector_partner_reset': '_onClickConnectorPartnerReset',
    }),

    xmlDependencies: (paymentSystemPage.prototype.xmlDependencies || []).concat(
        ["/payment_syncops/static/src/xml/connector.xml"]
    ),

    init: function () {
        this._super.apply(this, arguments);
        const self = this;
        this.connector = {
            dateFormat: 'DD-MM-YYYY',
        };
        this.connector.tools = {
            formatDate: (date) => moment(date).format(self.connector.dateFormat),
            formatCurrency: (amount, currency) => self.formatCurrency(amount, currency.position, currency.symbol, currency.precision),
        };
        this.connector.partner = {
            page: 1,
            pageSize: 5,
            list: [],
            flist: [],
            filter: false,
            getRows: () => self.connector.partner.filter && self.connector.partner.flist || self.connector.partner.list,
            lines: 'payment_syncops.partner_list_line',
            $lines: () => $('.o_connector_partner_table tbody'),
        };
        this.connector.ledger = {
            page: 1,
            pageSize: 10,
            list: [],
            getRows: () => self.connector.ledger.list,
            lines: 'payment_syncops.partner_ledger_line',
            $lines: () => $('.o_connector_partner_ledger_table tbody'),
        };
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            let $ledger_button = $('.o_connector_partner_ledger_date');
            if ($ledger_button.length) {
                $ledger_button.click(self._onClickConnectorPartnerLedgerDate.bind(self));
                self._getConnectorPartnerLedgerList();
            }
        });
    },

    _onClickConnectorPartnerGet: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        framework.showLoading();
        if (!this.connector.partner.list.length) {
            const self = this;
            rpc.query({route: '/my/payment/partners'}).then(function (partners) {
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
        const popup = new dialog(this, {
            title: _t('Select a partner'),
            $content: qweb.render('payment_syncops.partner_list', {}),
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
                        vat: $el.data('vat'),
                        ref: $el.data('ref'),
                        company: $el.data('company'),
                    },
                }).then(function (result) {
                    $el.prop({'disabled': 'disabled'}).addClass('disabled');
                    $('input#campaign').val($el.data('campaign') || '');
                    $('label[for="partner"] + span').text($el.data('company'));
                    $('.o_connector_partner_balance').html(result.render);
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
        var partners = partner.list;
        if (query) {
            let regex = new RegExp(query, 'i');
            partners = partners.filter((p) => p.company_name.match(regex));
            partner.flist = partners;
            partner.filter = true;
        } else {
            partner.flist = [];
            partner.filter = false;
        }
        this._renderConnectorPages('partner');
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
        const format = $('#date_start').data('date-format')
        framework.showLoading();
        rpc.query({
            route: '/my/payment/partners/ledger/list',
            params: {
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
            const render = qweb.render('payment_syncops.partner_ledger_line', {ledgers: []});
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
        const buttons = qweb.render('payment_syncops.pages', {pages: pages, page: page, type: type});
        $('.o_connector_pages').html(buttons);

        const firstLine = (page - 1) * pageSize;
        const lines = qweb.render(connector.lines, {
            rows: connector.getRows().slice(firstLine, firstLine + pageSize),
            tools: this.connector.tools,
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
            $('input#campaign').val(result.campaign || '');
            $('label[for="partner"] + span').text(result.name);
            $('.o_connector_partner_balance').html(result.render);
            $el.addClass('d-none');
        });
    },
});

});