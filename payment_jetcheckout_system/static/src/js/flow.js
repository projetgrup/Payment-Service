/** @odoo-module alias=paylox.system.page.flow **/
'use strict';

import { _t } from 'web.core';
import rpc from 'web.rpc';
import publicWidget from 'web.public.widget';
import payloxPage from 'paylox.page';
import fields from 'paylox.fields';
import { format } from 'paylox.tools';

publicWidget.registry.payloxSystemPageDynamic = publicWidget.Widget.extend({
    selector: '.payment-dynamic',

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
        this.partner = new fields.integer({
            default: 0,
        });
        this.vat = new fields.string();
        this.system = new fields.string({
            default: false,
        });
        this.subsystem = new fields.string({
            default: false,
        });
        this.advance = new fields.boolean({
            default: false,
        });
        this.wizard = {
            vat: new fields.element(),
            partner: new fields.element(),
            amount: new fields.float({
                default: 0,
                events: [
                    ['update', this._onUpdateAmount],
                ],
                mask: payloxPage.prototype._maskAmount.bind(this),
            }),
            page: {
                loading: new fields.element(),
                login: new fields.element(),
                register: new fields.element(),
                welcome: new fields.element(),
                amount: new fields.element(),
                overlay: new fields.element(),
                /*section: {
                    all: new fields.element(),
                    amount: new fields.element(),
                    card: new fields.element(),
                    installment: new fields.element(),
                },*/
            },
            register: {
                name: new fields.element(),
                vat: new fields.element(),
                email: new fields.element(),
                phone: new fields.element(),
            },
            button: {
                login: {
                    done: new fields.element({
                        events: [['click', this._onClickLoginNext]],
                    }),
                },
                register: {
                    prev: new fields.element({
                        events: [['click', this._onClickRegisterPrev]],
                    }),
                    done: new fields.element({
                        events: [['click', this._onClickRegisterNext]],
                    }),
                },
                welcome: {
                    prev: new fields.element({
                        events: [['click', this._onClickWelcomePrev]],
                    }),
                    done: new fields.element({
                        events: [['click', this._onClickWelcomeNext]],
                    }),
                },
                amount: {
                    currency: new fields.element({
                        events: [['click', this._onClickAmountCurrency]],
                    }),
                    prev: new fields.element({
                        events: [['click', this._onClickAmountPrev]],
                    }),
                    next: new fields.element({
                        events: [['click', this._onClickAmountNext]],
                    }),
                    done: new fields.element({
                        events: [['click', this._onClickAmountNext]],
                    }),
                },
            }
        };
    },
 
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            payloxPage.prototype._setCurrency.apply(this);
            payloxPage.prototype._start.apply(this);

            // if (window.location.search) {
            //     window.history.replaceState(null, '', window.location.pathname);
            // } else {
            //     this.wizard.vat.value = '';
            // }

            //this.wizard.vat.value = '';
            this.wizard.page.login.$.addClass('show');
            this.wizard.page.loading.$.removeClass('show');
            setTimeout(() => {
                this.wizard.vat.$.focus();
                this.wizard.page.loading.$.addClass('invisible');
            }, 500);
        });
    },

    _onUpdateAmount: function () {
        this.wizard.amount._.updateValue();
        this.wizard.amount.$.data('value', this.wizard.amount.value);
    },
 
    _onPause: async function(time=0) {
        await new Promise(resolve => setTimeout(resolve, time));
    },

    _queryPartnerPostprocess: function(partner) {
        $('.payment-page span[name=partner]').text(partner.name || '-');
    },

    _queryPartnerNew: async function() {
        await this._onPause(500);
        this.wizard.vat.$.removeClass('border-danger');
        this.wizard.page.login.$.find('div[name=welcome]').removeClass('text-500');
        this.wizard.page.login.$.find('div[name=vat]').removeClass('text-danger').text(_t('Please enter your VAT number'));
        this.wizard.button.login.done.$.removeClass('border-danger text-danger');

        this.wizard.page.login.$.addClass('slide').removeClass('show');
        this.wizard.page.register.$.removeClass('invisible').addClass('slide show');

        this.wizard.page.login.$.removeClass('blur');
        this.wizard.page.loading.$.removeClass('show transparent');

        setTimeout(() => {
            this.wizard.page.loading.$.addClass('invisible');
        }, 500);
    },

    _onClickLoginNext: async function () {
        const self = this;
        this.wizard.page.loading.$.removeClass('invisible').addClass('show transparent');
        this.wizard.page.login.$.addClass('blur');

        let partner = {};
        try {
            if (this.wizard.vat.value === '11111111111') {
                await this._queryPartnerNew()
                return;
            }

            partner = await rpc.query({
                route: '/my/payment/query/partner',
                params: { vat: this.wizard.vat.value },
            });
            if (partner.vat === '11111111111') {
                this.wizard.register.vat.value = this.wizard.vat.value;
                await this._queryPartnerNew();
                return;
            }
        } catch {}

        if (!partner.id) {
            this.wizard.vat.$.addClass('border-danger');
            this.wizard.page.login.$.find('div[name=welcome]').addClass('text-500');
            this.wizard.page.login.$.find('div[name=vat]').addClass('text-danger').text(_t('This VAT seems invalid. Please try again.'));
            this.wizard.button.login.done.$.addClass('border-danger text-danger');
        } else {
            this.partner.value = partner.id;
            if (partner.items) {
                // Sum of amounts from related payment links are retrieved.
                // Update amount input and create payment link input.
                let amountTotal = 0;
                let amountInput = $('#payment_card input[name=amount]');
                for (const [id, amount] of partner.items) {
                    amountTotal += amount;
                    amountInput.after(`<input type="checkbox" class="input-switch d-none" data-id="${id}" data-paid="${amount}" disabled="disabled" checked="checked"/>`);
                }                    
                this.wizard.amount.$.val(format.float(amountTotal)).change().trigger('update');
            }

            this.vat.value = this.wizard.vat.value;
            this.wizard.partner.html = partner.name || '-';
            this._queryPartnerPostprocess(partner);

            this.wizard.vat.$.removeClass('border-danger');
            this.wizard.page.login.$.find('div[name=welcome]').removeClass('text-500');
            this.wizard.page.login.$.find('div[name=vat]').removeClass('text-danger').text(_t('Please enter your VAT number'));
            this.wizard.button.login.done.$.removeClass('border-danger text-danger');

            this.wizard.page.login.$.addClass('slide').removeClass('show');
            this.wizard.page.loading.$.removeClass('show transparent');
            self.wizard.page.welcome.$.removeClass('invisible').addClass('slide show');
            self.wizard.page.welcome.$.find('.welcome-box').addClass('show welcome-title');
            setTimeout(function() {
                self.wizard.page.welcome.$.find('.fade').addClass('show');
                self.wizard.page.login.$.removeClass('blur');
                self.wizard.page.loading.$.addClass('invisible');
            }, 1500);
        }
        this.wizard.page.login.$.removeClass('blur');
        this.wizard.page.loading.$.removeClass('show transparent');
        setTimeout(function() {
            self.wizard.page.loading.$.addClass('invisible');
        }, 500);
    },
 
    _onClickRegisterPrev: async function () {
        const self = this;
        this.wizard.page.register.$.removeClass('slide show');
        setTimeout(function() {
            self.wizard.page.register.$.addClass('invisible');
        }, 500);
        this.wizard.page.login.$.removeClass('slide invisible').addClass('show');
    },

    _onClickRegisterNext: async function () {
        const self = this;
        this.wizard.page.loading.$.removeClass('invisible').addClass('show transparent');
        this.wizard.page.register.$.addClass('blur');
 
        let partner = {};
        try {
            const params = {};
            for (const [name, field] of Object.entries(this.wizard.register)) {
                if (field instanceof fields.field && field.value) {
                    params[name] = field.value;
                }
            }
            partner = await rpc.query({
                route: '/my/payment/create/partner',
                params: params,
            });
        } catch {}

        if (!partner.id) {
            this._highlightWizardRegisterFields(partner.error);
        } else {
            this.partner.value = partner.id;
            this.vat.value = this.wizard.register.vat.value;
            this.wizard.partner.html = partner.name || '-';
            this._queryPartnerPostprocess(partner);
            this._clearWizardRegisterFields();

            this.wizard.page.register.$.addClass('slide').removeClass('show');
            self.wizard.page.welcome.$.removeClass('invisible').addClass('slide show');
            self.wizard.page.welcome.$.find('.welcome-box').addClass('show welcome-title');
            setTimeout(function() {
                self.wizard.page.welcome.$.find('.fade').addClass('show');
            }, 1500);
        }
        this.wizard.page.register.$.removeClass('blur');
        this.wizard.page.loading.$.removeClass('show transparent');
        setTimeout(function() {
            self.wizard.page.loading.$.addClass('invisible');
        }, 500);
    },
 
    _onClickWelcomePrev: async function () {
        const self = this;
        this.wizard.page.welcome.$.removeClass('slide show');
        setTimeout(function() {
            self.wizard.page.welcome.$.addClass('invisible');
        }, 500);
        this.wizard.page.welcome.$.find('.welcome-box').removeClass('show welcome-title');
        this.wizard.page.welcome.$.find('.fade').removeClass('show');
        this.wizard.page.login.$.removeClass('slide invisible').addClass('show');
    },

    _onClickWelcomeNext: async function () {
        this.wizard.page.welcome.$.addClass('slide').removeClass('show');

        const element = $('label[name=partner]').closest('.card');
        const offset = element.offset();
        const overlay = this.wizard.page.overlay.$;
        const position = {
            top:  offset.top - overlay.offset().top - 24,
            left: offset.left,
            width: element.outerWidth(),
            height: element.outerHeight(),
        }

        const $element = element.clone().addClass('payment-card-item-clone').attr('name', 'partner');
        $element.css('width', position.width).css('height', position.height);
        $element.find('span[name=partner]').html(this.wizard.partner.html);

        overlay.append($element);
        await this._onPause(100);
        $element.addClass('show');
        await this._onPause(750);
        $element.css('transform', 'translate(' + position.left + 'px, ' + position.top + 'px)');
        $('.payment-dynamic .col-md-3 .shine').addClass('transparent');

        setTimeout(() => this.wizard.page.welcome.$.addClass('invisible'), 500);
        //this.wizard.page.section.all.$.addClass('show');
        //this.wizard.page.section.amount.$.addClass('active');
        this.wizard.page.amount.$.removeClass('invisible').addClass('slide show');
    },

    _onClickAmountCurrency: function (ev) {
        if (ev.target.nodeName === 'LI') {
            payloxPage.prototype._updateCurrency.call(this, ev.target);
            payloxPage.prototype._setCurrency.apply(this);
            const $symbol = $('.payment-system .symbol');
            $symbol.removeClass('symbol-after symbol-before').addClass('symbol-' + ev.target.dataset.position);
            $symbol.text(ev.target.dataset.symbol);
            this.wizard.button.amount.currency.$.find('span').text(ev.target.dataset.name);
        }
    },

    _onClickAmountPrev: async function () {
        this.wizard.page.amount.$.removeClass('slide show');
        //this.wizard.page.section.all.$.removeClass('show');
        //this.wizard.page.section.amount.$.removeClass('active');

        const overlay = this.wizard.page.overlay.$;
        const $element = overlay.find('[name=partner]');
        $element.css('transform', '');
        $('.payment-dynamic .col-md-3 .shine').removeClass('transparent');
        await this._onPause(750);

        $element.removeClass('show');
        setTimeout(() => $element.remove(), 500);

        this.wizard.page.amount.$.addClass('invisible');
        this.wizard.page.welcome.$.removeClass('invisible').addClass('show');
    },

    _onClickAmountNext: async function () {
        this.wizard.page.amount.$.addClass('slide').removeClass('show');

        const element = $('label[for=amount]').closest('.card');
        const offset = element.offset();
        const overlay = this.wizard.page.overlay.$;
        const amount = this.wizard.amount.value;
        const position = {
            top:  offset.top - overlay.offset().top - 24,
            left: offset.left,
            width: element.outerWidth(),
            height: element.outerHeight(),
        }

        const $element = element.clone().addClass('payment-card-item-clone').attr('name', 'amount');
        $element.css('width', position.width).css('height', position.height);
        $element.find('input[name=amount]').removeAttr('id');
        $element.find('input[name=amount]').val(format.float(amount));
        $element.find('input[name=amount] + span.symbol').removeClass('symbol-after symbol-before').addClass('symbol-' + this.currency.position).text(this.currency.symbol);
        $element.find('button[field="button.currency"] span').text(this.currency.name);
        $('button[field="button.currency"] span').text(this.currency.name);

        overlay.append($element);
        await this._onPause(100);
        $element.addClass('show');
        await this._onPause(750);
        $element.css('transform', 'translate(' + position.left + 'px, ' + position.top + 'px)');
        await this._onPause(500);

        $('#payment_card input[name=amount]').val(format.float(amount)).change().trigger('update');
        const page = $('.payment-dynamic');
        overlay.css('opacity', '0');
        page.css('opacity', '0');
        //await this._onPause(500);
        //overlay.addClass('invisible');
        //page.addClass('invisible');
        setTimeout(() => overlay.remove(), 500);
        setTimeout(() => page.remove(), 500);
    },

    _highlightWizardRegisterFields: function (error) {
        this.wizard.button.register.done.$.addClass('border-danger text-danger');
        this.wizard.register.name.$.addClass('border-danger').siblings('label').addClass('text-danger');
        this.wizard.register.vat.$.addClass('border-danger').siblings('label').addClass('text-danger');
        this.wizard.register.email.$.addClass('border-danger').siblings('label').addClass('text-danger');
        this.wizard.register.phone.$.addClass('border-danger').siblings('label').addClass('text-danger');
        this.wizard.page.register.$.find('div[name=title]').addClass('text-500');
        this.wizard.page.register.$.find('div[name=text]').addClass('text-danger').html(error || _t('An error occured. Please try again.'));
    },

    _clearWizardRegisterFields: function () {
        this.wizard.button.register.done.$.removeClass('border-danger text-danger');
        this.wizard.register.name.$.removeClass('border-danger').siblings('label').removeClass('text-danger');
        this.wizard.register.vat.$.removeClass('border-danger').siblings('label').removeClass('text-danger');
        this.wizard.register.email.$.removeClass('border-danger').siblings('label').removeClass('text-danger');
        this.wizard.register.phone.$.removeClass('border-danger').siblings('label').removeClass('text-danger');
        this.wizard.page.register.$.find('div[name=title]').removeClass('text-500');
        this.wizard.page.register.$.find('div[name=text]').removeClass('text-danger').text(_t('Please enter your VAT number'));
    },
});

export default {
    dynamic: publicWidget.registry.payloxSystemPageDynamic,
};
