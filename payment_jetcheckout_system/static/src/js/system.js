/** @odoo-module alias=paylox.system.page **/
'use strict';

import rpc from 'web.rpc';
import core from 'web.core';
import utils from 'web.utils';
import config from 'web.config';
import dialog from 'web.Dialog';
import publicWidget from 'web.public.widget';
import framework from 'paylox.framework';
import payloxPage from 'paylox.page';
import fields from 'paylox.fields';
import { format } from 'paylox.tools';

const _t = core._t;
const qweb = core.qweb;

payloxPage.include({
    init: function (parent, options) {
        this._super(parent, options);
        this.system = new fields.string({
            default: false,
        });
    },

    _getParams: function () {
        let params = this._super.apply(this, arguments);
        let payments = [];
        let items = [];
        let payment_tag = false;
        let sale_ref = false;
        let $sale_ref = $('div.payment-saleref');
        if ($sale_ref.length && !$sale_ref.hasClass('d-none')) {
            sale_ref = $sale_ref.find('input').val();
        } else {
            let $items = $('input.input-switch:checked');
            if ($items.length) {
                $items.each(function () {
                    let $this = $(this);
                    let id = parseInt($this.data('id'));
                    let amount = parseFloat($this.data('amount'));
                    payments.push(id);
                    items.push([id, amount]);
                });
                let $payment_tag = $('button[field="payment.due.tag"].btn-primary');
                if ($payment_tag.length) {
                    payment_tag = parseInt($payment_tag[0].dataset.id);
                }
            }
        }
        params['system'] = this.system.value;
        params['items'] = items;
        params['payments'] = payments;
        params['payment_tag'] = payment_tag;
        params['sale_ref'] = sale_ref;
        return params;
    },

    _checkData: function () {
        var $items = $('input.input-switch');
        if (!$items.length) {
            return this._super.apply(this, arguments);
        }

        var $items = $('input.input-switch:checked');
        if (!$items.length) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please select at least one payment'),
            });
            this._enableButton();
            return false;
        } else {
            return this._super.apply(this, arguments);
        }
    },

});

publicWidget.registry.payloxPaymentCompany = publicWidget.Widget.extend({
    selector: '.payment-company',

    init: function (parent, options) {
        this._super(parent, options);
        this.payment = {
            company: new fields.element({
                events: [['click', this._onClickCompany]],
            }),
        };
    },
 
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            payloxPage.prototype._start.apply(this);
        });
    },

    _onClickCompany: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (!window.location.pathname.includes('/my/')) {
            return;
        }

        const $button = $(ev.currentTarget);
        const cid = $button.data('id');
        rpc.query({ route: '/my/payment/company', params: { cid } }).then((result) => {
            if (result) {
                framework.showLoading();
                window.location.reload();
            }
        });
    },
});

publicWidget.registry.payloxSystemPage = publicWidget.Widget.extend({
    selector: '.payment-system',
    jsLibs: ['/payment_jetcheckout/static/src/lib/imask.js'],
    xmlDependencies: ['/payment_jetcheckout_system/static/src/xml/system.xml'],

    init: function (parent, options) {
        this._super(parent, options);
        this.currency = {
            id: 0,
            decimal: 2,
            name: '',
            separator: '.',
            thousand: ',', 
            position: 'after',
            symbol: '', 
        };
        this.isPreview = false;
        this.itemPriority = false;
        this.amountEditable = false;
        this.amount = new fields.float({
            events: [
                ['update', function() { this.amount._.updateValue(); }],
            ],
            mask: payloxPage.prototype._maskAmount.bind(this),
            default: 0,
        });
        this.partner = new fields.integer({
            default: 0,
        });
        this.vat = new fields.string();
        this.campaign = {
            name: new fields.string(),
            text: new fields.string(),
        };
        this.payment = {
            amount: new fields.float({
                events: [
                    ['input', this._onInputAmount],
                    ['update', this._onUpdateAmount],
                    ['change', this._onChangeAmount],
                ],
                mask: payloxPage.prototype._maskAmount.bind(this),
                default: 0,
            }),
            company: new fields.element({
                events: [['click', this._onClickCompany]],
            }),
            tag: new fields.element({
                events: [['click', this._onClickTag]],
            }),
            tags: new fields.element({
                events: [['click', this._onClickTags]],
            }),
            privacy: new fields.element({
                events: [['click', this._onClickPrivacy]],
            }),
            agreement: new fields.element({
                events: [['click', this._onClickAgreement]],
            }),
            membership: new fields.element({
                events: [['click', this._onClickMembership]],
            }),
            contact: new fields.element({
                events: [['click', this._onClickContact]],
            }),
            item: new fields.element({
                events: [['change', this._onChangePaid]],
            }),
            items: new fields.element({
                events: [['change', this._onChangePaidAll]],
            }),
            itemAddDateReadonly: new fields.element(),
            itemAddDescMaxlength: new fields.element(),
            itemAddDescPrefix: new fields.element(),
            itemAdd: new fields.element({
                events: [['click', this._onClickItemAdd]],
            }),
            itemRemove: new fields.element({
                events: [['click', this._onClickItemRemove]],
            }),
            itemsBtn: new fields.element({
                events: [['click', this._onChangePaidAllBtn]],
            }),
            link: new fields.element({
                events: [['click', this._onClickLink]],
            }),
            sharelink: new fields.element({
                events: [['click', this._onClickLinkCopy]],
            }),
            sharemail: new fields.element({
                events: [['click', this._onClickLinkShare]],
            }),
            sharesms: new fields.element({
                events: [['click', this._onClickLinkShare]],
            }),
            shareqr: new fields.element(),
            contactless: new fields.element(),
            pivot: new fields.element(),
            priority: new fields.element(),
            preview: {
                grid: new fields.element(),
                print: new fields.element({
                    events: [['click', this._onClickPreviewPrint]],
                }),
                campaign: new fields.element({
                    events: [['click', this._onClickPreviewCampaign]],
                }),
            },
            due: {
                date: new fields.element(),
                days: new fields.element(),
                payment: new fields.element(),
                warning: new fields.element(),
                tag: new fields.element({
                    events: [['click', this._onClickDueTag]],
                }),
            },
            advance: {
                amount: 0,
                add: new fields.element({
                    events: [['click', this._onClickAdvanceAdd]],
                }),
                remove: new fields.element({
                    events: [['click', this._onClickAdvanceRemove]],
                }),
            },
            saleRef: {
                button: new fields.element({
                    events: [['click', this._onClickSaleRefButton]],
                }),
                value: new fields.string(),
                ok: false,
            },
        };
    },

    start: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            payloxPage.prototype._setCurrency.apply(self);
            payloxPage.prototype._start.apply(self);
            if (self.payment.item.exist) {
                self.itemPriority = self.payment.priority.exist;
                self.amountEditable = self.payment.amount.exist;
                self._onChangePaid();
            } else if (self.payment.preview.grid.exist) {
                self.isPreview = true;
                self.amount = new fields.float({
                    events: [
                        ['input', self._onInputRawAmount],
                    ],
                    default: 0,
                    mask: payloxPage.prototype._maskAmount.bind(self),
                });
                payloxPage.prototype._start.apply(self, ['amount']);
                self._getPreviewGrid();
            }
            if (self.payment.shareqr.exist) {
                self.amount.$.change(() => {
                    const params = self._prepareLink();
                    const link = window.location.origin + window.location.pathname + '?=' + encodeURIComponent(btoa(params));
                    self.payment.shareqr.$[0].src = '/report/barcode/?type=QR&width=160&height=160&value=' + link;
                });
            }
        });
    },

    _getPreviewGrid: async function () {
        let grid = false;
        await rpc.query({
            route: '/payment/card/installments',
            params: {
                amount: this.amount.value,
                currency: this.currency.id,
                campaign: this.campaign.name.value,
            },
        }).then((result) => {
            if ('error' in result) {
                grid = false;
                this.displayNotification({
                    type: 'warning',
                    title: _t('Warning'),
                    message: _t('An error occured.') + ' ' + result.error,
                });
            } else {
                grid = result;
            }
        }).guardedCatch(() => {
            grid = false;
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please contact with your system administrator.'),
            });
        });

        if (grid) {
            this.payment.preview.grid.html = qweb.render('paylox.installment.grid', {
                value: this.amount.value,
                format: {...format, type: payloxPage.prototype._getCardType},
                ...this.currency,
                ...grid,
            });

            $('.installment-table picture > img').on('load', function () {
                $(this).removeClass('d-none');
                $('.installment-table picture').removeClass('placeholder');
            });
        } else {
            this.payment.preview.grid.html = `<h2 class="text-600 mt-4">${_t('No payment information found')}</h2>`;
            $('.installment-table picture > img').off('load', null);
        }
    },

    _onClickPreviewPrint: async function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (this.isPreview) {
            window.print();
        }
    },

    _onClickPreviewCampaign: async function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (this.isPreview) {
            let campaigns = false;
            let self = this;
            await rpc.query({
                route: '/payment/card/campaigns',
            }).then(function (result) {
                campaigns = result;
            }).guardedCatch(function (error) {
                self.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: _t('An error occured. Please contact with your system administrator.'),
                });
                if (config.isDebug()) {
                    console.error(error);
                }
            });

            if (campaigns) {
                let popup = new dialog(self, {
                    title: _t('Campaigns Table'),
                    size: 'small',
                    buttons: [{
                        close: true,
                        text: _t('Cancel'),
                        classes: 'btn-secondary text-white',
                    }],
                    $content: qweb.render('paylox.campaigns', { campaigns, current: this.campaign.name.value })
                });

                popup.open().opened(function () {
                    popup.$modal.addClass('payment-page');
                    let $button = $('.modal-body button.o_button_select_campaign');
                    $button.click(function(e) {
                        let campaign = e.currentTarget.dataset.name;
                        self.campaign.name.value = campaign;
                        self.campaign.name.$.trigger('change');
                        self._getPreviewGrid();
                        popup.destroy();
                    });
                });
            }
        }
    },

    _onInputRawAmount: function () {
        if (this.isPreview) {
            clearTimeout(this.debounce);
            this.debounce = setTimeout(() => {
                this._getPreviewGrid();
            }, 500);
        }
    },

    _onInputAmount: function () {
        const currency = this.currency;
        const inputs = $('input.input-switch');
        let amount = this.payment.amount.value;
        inputs.each(function () {
            const input = $(this);
            const payable = input.closest('tr').find('.item-amount-payable');
            const residual = parseFloat(input.data('payable') || 0.0);
            if (amount < 0) {
                amount = 0;
            }

            const value = residual > amount ? amount : residual;
            if (amount > 0) {
                payable.html(format.currency(value, currency.position, currency.symbol, currency.decimal));
                input.prop('checked', true);
                input.data('amount', value);
                amount -= residual;
            } else {
                payable.html(format.currency(0, currency.position, currency.symbol, currency.decimal));
                input.prop('checked', false);
                input.data('amount', 0);
            }
        });
        this._onChangePaid({
            allTarget: true,
        });
        //const amounts = inputs.map(function() { return parseFloat($(this).data('amount')); }).get();
    },

    _onUpdateAmount: function () {
        this.payment.amount._.updateValue();
    },

    _onChangeAmount: function (ev) {
        let amount = 0;
        let items = this.payment.item.$.filter(function () {
            return $(this).hasClass('input-switch');
        });
        items.each(function () {
            amount += parseFloat($(this).data('amount'));
        });

        if (amount < this.payment.amount.value) {
            this.payment.advance.amount = this.payment.amount.value - amount;
            this._onClickAdvanceAdd(ev);
        }
    },

    _applyPriority: function () {
        if (this.itemPriority) {
            const items = this.payment.item.$;
            items.parent().addClass('disabled');

            const checks = items.filter(function() {
                const $this = $(this);
                return $this.hasClass('input-switch') && $this.is(':checked');
            });
            const last = checks.last();

            const unchecks = items.filter(function() {
                const $this = $(this);
                return $this.hasClass('input-switch') && !$this.is(':checked');
            });
            const first = unchecks.first();

            $('input[type="checkbox"][data-id="' + parseInt(last.data('id')) + '"].payment-items').parent().removeClass('disabled');
            $('input[type="checkbox"][data-id="' + parseInt(first.data('id')) + '"].payment-items').parent().removeClass('disabled');
        }
    },

    _onChangePaidAllBtn: function (ev) {
        const $input = $(ev.currentTarget).find('input');
        $input.prop('checked', !$input.prop('checked'));
        $input.trigger('change');
    },

    _onChangePaidAll: function (ev) {
        const checked = $(ev.currentTarget).is(':checked');
        this.payment.items.checked = checked;
        this.payment.item.checked = checked;
        this._onChangePaid(ev);
    },

    _getDueTag: function () {
        if (this.payment.due.tag.exist) {
            let tag = this.payment.due.tag.$.filter('.btn-primary');
            return tag && tag.data('tag') || '';
        }
        return false;
    },

    _onChangePaid: function (ev) {
        if (!this.amount.exist) {
            return;
        }

        let currency = this.currency;
        if (ev && ev.currentTarget) {
            let $input = $(ev.currentTarget);
            let id = parseInt($input.data('id'));
            let checked = $input.prop('checked');

            let $inputs = $('input[type="checkbox"][data-id="' + id + '"].payment-items');
            $inputs.each(function () { $(this).prop('checked', checked); });

            let $switches = $('input[type="checkbox"].payment-items.input-switch');
            $switches.each(function () {
                let $this = $(this);
                $this.data('amount', $this.is(':checked') ? parseFloat($this.data('payable')) : 0);
                let $payable = input.closest('tr').find('.item-amount-payable');
                $payable.html(format.currency(parseFloat($this.data('amount')), currency.position, currency.symbol, currency.decimal));
            });
        } else if (ev && ev.allTarget) {
            let $inputs = $('input.input-switch');
            $inputs.each(function () {
                let $input = $(this);
                let id = parseInt($input.data('id'));
                let checked = $input.prop('checked');
                $('input[type="checkbox"][data-id="' + id + '"].payment-items').prop('checked', checked);
            });
        }

        let $total = $('div.payment-amount-total');
        let $items = $('input.input-switch:checked');
        this.payment.items.checked = !!$items.length;

        if (this.payment.due.payment.exist) {
            let items = $items.map(function() {
                let $this = $(this);
                return [[parseInt($this.data('id')), parseFloat($this.data('amount'))]];
            }).get();

            rpc.query({
                route: '/p/due',
                params: { items, tag: this._getDueTag() }
            }).then((result) => {
                if (result.advance_amount > 0) {
                    this.payment.advance.add.html = _.str.sprintf(
                        _t('Click here for getting <span class="text-primary">%s</span> campaign by adding <span class="text-primary">%s</span> advance payment'),
                        result.advance_campaign,
                        format.currency(result.advance_amount, currency.position, currency.symbol, currency.decimal)
                    );
                    this.payment.advance.amount = result.advance_amount;
                } else {
                    this.payment.advance.add.html = '';
                    this.payment.advance.amount = 0;
                }
                this.payment.due.date.html = result.date;
                this.payment.due.days.html = result.days;
                this.campaign.text.html = result.campaign;
                this.campaign.name.value = result.campaign;
                this.campaign.name.$.trigger('change', [{ locked: true }]);
                if (result.hide_payment) {
                    this.payment.due.warning.$.removeClass('d-none');
                    this.payment.due.warning.$.find('p').text(result.hide_payment_message);
                    this.payment.due.payment.$.addClass('d-none');
                } else {
                    this.payment.due.warning.$.addClass('d-none');
                    this.payment.due.warning.$.find('p').text('');
                    this.payment.due.payment.$.removeClass('d-none');
                }
            });
        }

        this._applyPriority();
 
        let amount = 0;
        $items.each(function() { amount += parseFloat($(this).data('amount') || 0.0); });

        this.amount.value = format.float(amount);
        this.amount.$.trigger('update');

        if (this.amountEditable) {
            if (ev && ev.allTarget) {
                return;
            }
            this.payment.amount.value = format.float(amount, currency.decimal);
            this.payment.amount.$.trigger('update');
        } else {
            $total.html(format.currency(amount, currency.position, currency.symbol, currency.decimal));
        }
    },
 
    _onClickItemAdd: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const popup = new dialog(this, {
            title: _t('Add Payment Item'),
            size: 'small',
            buttons: [{
                text: _t('Add'),
                classes: 'btn-block btn-primary font-weight-bold',
            }],
            $content: qweb.render('paylox.item.add', {
                currency: this.currency,
                date: moment().format('DD-MM-YYYY'),
                readonly: this.payment.itemAddDateReadonly.exist || undefined,
                maxlength: this.payment.itemAddDescMaxlength.value || undefined,
                prefix: this.payment.itemAddDescPrefix.value || '',
            })
        });

        popup.opened(() => {
            const $date = popup.$modal.find('input#payment_item_add_date');
            const $desc = popup.$modal.find('input#payment_item_add_desc');
            const $amount = popup.$modal.find('input#payment_item_add_amount');
            const mask = payloxPage.prototype._maskAmount.apply(this);
            const amount = new IMask($amount[0], mask);

            const $footer = popup.$modal.find('footer');
            $footer.css('box-shadow', '0 10px 10px -5px #ccc inset');

            const $button = popup.$modal.find('footer button');
            $button.click(() => {
                framework.showLoading();
                $date.prop('disabled', true);
                $desc.prop('disabled', true);
                $amount.prop('disabled', true);
                $button.prop('disabled', true);
                const context = this._getContext();
                rpc.query({
                    route: '/p/item/add',
                    params: { date: $date.val(), desc: $desc.val(), amount: amount.typedValue, lang: context.lang },
                }).then(([payments, company]) => {
                    $('.payment-item').html(qweb.render('paylox.item.all', {
                        payments,
                        company,
                        format,
                        prioritize: this.itemPriority,
                        currency: this.currency
                    }));
                    payloxPage.prototype._start.apply(this, [
                        'payment.item',
                        'payment.items',
                        'payment.itemsBtn',
                        'payment.itemRemove',
                        'payment.due.date',
                        'payment.due.days',
                        'payment.advance.add',
                        'payment.advance.remove',
                    ]);
                    this._onChangePaid();
                }).guardedCatch(() => {
                    this.displayNotification({
                        type: 'danger',
                        title: _t('Error'),
                        message: _t('An error occured. Please try again.'),
                        sticky: false,
                    });
                }).finally(() => {
                    popup.destroy();
                    framework.hideLoading();
                });
            });
        });
        popup.open();
    },

    _onClickItemRemove: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        framework.showLoading();

        rpc.query({
            route: '/p/item/remove',
            params: { pid: $(ev.currentTarget).data('id') }
        }).then(([payments, company]) => {
            $('.payment-item').html(qweb.render('paylox.item.all', {
                payments,
                company,
                format,
                prioritize: this.itemPriority,
                currency: this.currency
            }));
            payloxPage.prototype._start.apply(this, [
                'payment.item',
                'payment.items',
                'payment.itemsBtn',
                'payment.itemRemove',
                'payment.due.date',
                'payment.due.days',
                'payment.advance.add',
                'payment.advance.remove',
            ]);
            this._onChangePaid();
        }).guardedCatch(() => {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please try again.'),
                sticky: false,
            });
        });
        framework.hideLoading();
    },

    _onClickAdvanceAdd: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        framework.showLoading();

        rpc.query({
            route: '/p/advance/add',
            params: { amount: this.payment.advance.amount, tag: this._getDueTag() }
        }).then(([payments, company]) => {
            $('.payment-item').html(qweb.render('paylox.item.all', {
                payments,
                company,
                format,
                prioritize: this.itemPriority,
                currency: this.currency
            }));
            payloxPage.prototype._start.apply(this, [
                'payment.item',
                'payment.items',
                'payment.itemsBtn',
                'payment.itemRemove',
                'payment.due.date',
                'payment.due.days',
                'payment.advance.add',
                'payment.advance.remove',
            ]);
            this._onChangePaid();
        }).guardedCatch(() => {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please try again.'),
                sticky: false,
            });
        });
        framework.hideLoading();
    },

    _onClickAdvanceRemove: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        framework.showLoading();

        rpc.query({
            route: '/p/advance/remove',
            params: { pid: $(ev.currentTarget).data('id'), tag: this._getDueTag() }
        }).then(([payments, company]) => {
            $('.payment-item').html(qweb.render('paylox.item.all', {
                payments,
                company,
                format,
                prioritize: this.itemPriority,
                currency: this.currency
            }));
            payloxPage.prototype._start.apply(this, [
                'payment.item',
                'payment.items',
                'payment.itemsBtn',
                'payment.itemRemove',
                'payment.due.date',
                'payment.due.days',
                'payment.advance.add',
                'payment.advance.remove',
            ]);
            this._onChangePaid();
        }).guardedCatch(() => {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please try again.'),
                sticky: false,
            });
        });
        framework.hideLoading();
    },

    _onClickSaleRefButton: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (this.payment.saleRef.ok) {
            $('.payment-item').removeClass('d-none');
            $('.payment-saleref').addClass('d-none');
            $('.payment-amount-total-readonly').removeClass('d-none');
            $('.payment-amount-total-editonly').addClass('d-none');
            this.payment.saleRef.button.text = _t('Pay with payment items');
            this.payment.saleRef.ok = false;
        } else {
            $('.payment-item').addClass('d-none');
            $('.payment-saleref').removeClass('d-none');
            $('.payment-amount-total-readonly').addClass('d-none');
            $('.payment-amount-total-editonly').removeClass('d-none');
            this.payment.saleRef.button.text = _t('Pay with sale reference');
            this.payment.saleRef.ok = true;
        }
    },

    _onClickCompany: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (!window.location.pathname.includes('/p/')) {
            return;
        }

        const $button = $(ev.currentTarget);
        const cid = $button.data('id');
        rpc.query({route: '/p/company', params: { cid }}).then((token) => {
            if (token) {
                framework.showLoading();
                window.location.assign('/p/' + token);
            }
        });
    },

    _onClickTag: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const $button = $(ev.currentTarget);
        const tid = $button.data('id');
        rpc.query({route: '/p/tag', params: { tid }}).then((token) => {
            if (token) {
                framework.showLoading();
                window.location.assign('/p/' + token);
            }

        });
    },

    _onClickTags: function (ev) {
        const $button = $(ev.currentTarget);
        const pid = parseInt($button.data('id'));
        $button.toggleClass('btn-light');

        _.each(this.payment.item.$, function(item) {
            const $el = $(item);
            if ($el.data('type-id') === pid) {
                if ($button.hasClass('btn-light')) {
                    $el.prop('checked', false);
                    $el.closest('tr').addClass('d-none');
                } else {
                    $el.prop('checked', true);
                    $el.closest('tr').removeClass('d-none');
                }
            }
        });
        this._onChangePaid();
    },

    _onClickDueTag: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        let $button = $(ev.currentTarget);
        if ($button.hasClass('btn-primary')) {
            return;
        }
        let $buttons = $('button[field="payment.due.tag"].btn-primary');

        framework.showLoading();
        $buttons.removeClass('btn-primary').addClass('btn-secondary');
        $button.removeClass('btn-secondary').addClass('btn-primary');

        let tag = $button.data('id') || false;
        if (tag) {
            tag = parseInt(tag);
        }

        rpc.query({route: '/p/due/tag', params: { tag }}).then(([payments, company]) => {
            $('.payment-item').html(qweb.render('paylox.item.all', {
                payments,
                company,
                format,
                prioritize: this.itemPriority,
                currency: this.currency
            }));
            payloxPage.prototype._start.apply(this, [
                'payment.item',
                'payment.items',
                'payment.itemsBtn',
                'payment.itemRemove',
                'payment.due.date',
                'payment.due.days',
                'payment.advance.add',
                'payment.advance.remove',
            ]);

            if (company.campaign) {
                this.campaign.text.html = company.campaign;
                this.campaign.name.value = company.campaign;
                this.campaign.name.$.trigger('change', [{ locked: true }]);

                this.payment.due.warning.$.addClass('d-none');
                this.payment.due.warning.$.find('p').text('');
                this.payment.due.payment.$.removeClass('d-none');
            }
            this._onChangePaid();
        }).guardedCatch(() => {
            $buttons.removeClass('btn-secondary').addClass('btn-primary');
            $button.removeClass('btn-primary').addClass('btn-secondary');
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please contact with your system administrator.'),
            });
        });
        framework.hideLoading();
    },

    _onClickPrivacy: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        rpc.query({route: '/p/privacy'}).then(function (content) {
            new dialog(this, {
                title: _t('Privacy Policy'),
                $content: $('<div/>').html(content),
            }).open();
        });
    },

    _onClickAgreement: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        rpc.query({route: '/p/agreement'}).then(function (content) {
            new dialog(this, {
                title: _t('Distant Sale Agreement'),
                $content: $('<div/>').html(content),
            }).open();
        });
    },

    _onClickMembership: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        rpc.query({route: '/p/membership'}).then(function (content) {
            new dialog(this, {
                title: _t('Membership Agreement'),
                $content: $('<div/>').html(content),
            }).open();
        });
    },

    _onClickContact: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        rpc.query({route: '/p/contact'}).then(function (content) {
            new dialog(this, {
                title: _t('Contact Information'),
                $content: $('<div/>').html(content),
            }).open();
        });
    },

    _prepareLink: function() {
        const websiteID = $('html').data('websiteId') || 0;
        const amount = parseFloat(this.amount.value || 0);
        return JSON.stringify({
            id: websiteID,
            currency: this.currency.name,
            vat: this.vat.value,
            amount,
        });
    },

    _onClickLink: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this._onClickLinkCopy(ev, true);

        setTimeout(() => {
            $('.o_notification_manager').css('z-index', 999);
            $('.o_notification_body .o_button_link_send').off('click').on('click', (ev) => {
                this._onClickLinkShare(ev);
            });
        }, 500);
    },

    _onClickLinkCopy: async function (ev, popup) {
        ev.stopPropagation();
        ev.preventDefault();

        const params = this._prepareLink();
        const link = window.location.origin + window.location.pathname + '?=' + encodeURIComponent(btoa(params));
        navigator.clipboard.writeText(link);

        if (popup) {
            let content = qweb.render('paylox.item.link', { link });
            this.displayNotification({
                type: 'info',
                title: _t('Payment link is ready'),
                message: utils.Markup(content),
                sticky: true,
            });
        } else {
            this.displayNotification({
                type: 'info',
                title: _t('Success'),
                message: _t('Payment link has been copied'),
            });
        }
    },

    _onClickLinkShare: async function (ev, link) {
        ev.stopPropagation();
        ev.preventDefault();

        if (!link) {
            const params = this._prepareLink();
            link = window.location.origin + window.location.pathname + '?=' + encodeURIComponent(btoa(params));
        }

        const type = ev.currentTarget.dataset.type;
        const popup = new dialog(this, {
            title: _t('Share Payment Link'),
            size: 'small',
            buttons: [{
                text: _t('Share'),
                classes: 'btn-block btn-primary font-weight-bold',
            }],
            $content: qweb.render(`paylox.item.link.${type}`, {})
        });

        popup.opened(() => {
            popup.$modal.addClass('payment-page');
            const $button = popup.$modal.find('footer button');
            $button.click(() => {
                $button.prop('disabled', true);
                const $input = popup.$modal.find('input');
                const context = this._getContext();
                rpc.query({
                    route: '/my/payment/share/link',
                    params: { type, link, lang: context.lang, value: $input.val() },
                }).then((result) => {
                    if ('error' in result) {
                        this.displayNotification({
                            type: 'warning',
                            title: _t('Warning'),
                            message: _t('An error occured.') + ' ' + result.error,
                        });
                    } else {
                        this.displayNotification({
                            type: 'info',
                            title: _t('Success'),
                            message: result.message,
                        });
                    }
                }).guardedCatch(() => {
                    this.displayNotification({
                        type: 'danger',
                        title: _t('Error'),
                        message: _t('An error occured. Please contact with your system administrator.'),
                    });
                }).finally(() => {
                    popup.destroy();
                });
            });
        });

        popup.open();
    },
});

publicWidget.registry.payloxSystemPageTransaction = publicWidget.Widget.extend({
    selector: '.payment-page-transaction #wrapwrap',
    events: {
        'click .o_payment_transaction_apply': '_onClickApply',
        'click .o_payment_transaction_download': '_onClickDownload',
        'click .pagination .page-item .page-link': '_onClickPage',
    },

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            $('input.o_preloading').addClass('d-none');
            $('select#state').removeClass('d-none').select2({
                dropdownCssClass: 'o_payment_select2_dropdown',
            });
            framework.hideLoading();
        });
    },

    _onClickApply: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this._renderPage(document.querySelector('.pagination .page-item.active a'));
    },

    _onClickPage: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this._renderPage(ev.currentTarget);
    },

    _onClickDownload: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this._downloadPage();
    },

    _prepareParams: function (page) {
        if (page) {
            page = page.getAttribute('href');
            page = page ? Number(page.split('/').at(-1)) : 1;
        } else {
            page = 1;
        }

        const $start = $('#date_start');
        const $end = $('#date_end');
        const $state = $('#state');
        const format = $start.data('date-format');

        return {
            start: $start.val(),
            end: $end.val(),
            state: $state.val(),
            format: format,
            page: page,
        } 
    },

    _renderPage: function (page) {
        const params = this._prepareParams(page);
        const paths = window.location.pathname.split('/');
        while (!['my', 'p'].includes(paths[0])) {
            paths.shift();
            if (!paths.length) {
                return;
            }
        }
        const route = `/${paths[0]}/${paths[1]}/transaction/list`

        framework.showLoading();
        rpc.query({ route, params }).then((result) => {
            if (result.error) {
                this.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: result.error,
                });
            } else {
                $('.o_payment_transaction_list').html(result.page);
                $('.o_payment_transaction_pager').html(result.pager);
                $('.table-fold tr.row-view').on('click', function() {
                    $(this).toggleClass('open').next('.row-fold').toggleClass('open');
                });
            }
            framework.hideLoading();
        }).guardedCatch(() => {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured.'),
            });
            framework.hideLoading();
        });
    },

    _downloadPage: function () {
        const params = this._prepareParams();
        const query = new URLSearchParams(params);

        let state = false;
        framework.showLoading();

        const iframe = document.createElement('iframe');
        iframe.classList.add('d-none');
        iframe.setAttribute('src', window.location.origin + window.location.pathname  + '/download?' + query.toString());

        iframe.onload = (ev) => {
            if ($(ev.currentTarget).contents().find('title').first().text().includes('Error')) {
                this.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: _t('An error occured.'),
                });
                framework.hideLoading();
                iframe.remove(); 
            } else {
                this.displayNotification({
                    type: 'info',
                    title: _t('Ready'),
                    message: _t('Transactions are ready to download'),
                });
                framework.hideLoading();
                iframe.remove();
            }
        }
        iframe.onerror = (ev) => {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured.'),
            });
            framework.hideLoading();
            iframe.remove();
        }

        document.body.appendChild(iframe);
        this.displayNotification({
            type: 'info',
            title: _t('Ready'),
            message: _t('Transactions are ready to download'),
        });
        framework.hideLoading();
        setTimeout(() => {
            if (iframe) iframe.remove();
        }, 5000)
    }
});
 
export default publicWidget.registry.payloxSystemPage;
