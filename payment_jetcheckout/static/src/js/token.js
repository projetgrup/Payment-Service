/** @odoo-module alias=paylox.token.verify.page **/
'use strict';

import { _t } from 'web.core';
import publicWidget from 'web.public.widget';
import payloxPage from 'paylox.page';
//import fields from 'paylox.fields';

publicWidget.registry.payloxTokenVerify = payloxPage.extend({
    selector: '.payment-token-verify #wrapwrap',

    /*init: function (parent, options) {
        this._super(parent, options);
        this.verify = new fields.element({
            events: [['click', this._onClickVerify]],
        });
    },*/

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            const iframe = window.parent.document.querySelector('.o_form_payment_token_verify iframe');
            if (iframe) {
                iframe.classList.add('bg-white');
            } else {
                document.body.classList.add('d-none');
            }
            setInterval(() => $('.o_loading em').removeClass('d-none'), 2000);
        });
    },

    _checkData: function () {
        let checked = true;
        if (!this.card.holder.value) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please fill card holder name'),
            });
            checked = false;
        } else if (!this.card.number.value) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please fill card number'),
            });
            checked = false;
        } else if (!this.card.valid) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please enter a valid card number'),
            });
            checked = false;
        } else if (!this.card.date.value) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please fill card expiration date'),
            });
            checked = false;
        } else if (!this.card.code.value) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please fill card security code'),
            });
            checked = false;
        }

        return checked;
    },

    _getParams: function () {
        const data = JSON.parse(window.parent.document.querySelector('.o_form_payment_token_verify iframe + span').textContent);
        const rows = this.installment.rows || [];
        rows.forEach(i => i.idesc = _t('Card Verification'));
        return {
            type: 'virtual_pos',
            verify: true,
            card: {
                type: this.card.type || '',
                family: this.card.family || '',
                code: this.card.code.value,
                holder: this.card.holder.value,
                date: this.card.date.value,
                number: this.card.number.value,
                token: data.id,
            },
            amount: this.amount.value,
            currency: this.currency.id,
            installment: {
                id: 1,
                index: 0,
                rows: rows,
            },
            partner: parseInt(this.partner.value || 0),
            campaign: this.campaign.name.value || '',
            successurl: this.payment.successurl.value,
            failurl: this.payment.failurl.value,
        }
    },

    _updateCurrency: function () {},
    _onChangeCampaign: function () {},
    _onClickAmountCurrency: function () {},
    _onClickPaymentTerms: function () {},
    _onClickInstallmentTable: function () {},
    _onClickCampaingTable: function () {},
    _onClickRow: function () {},
    _onClickInstallmentCredit: function () {},
    _onInputAmount: function () {},
    _onUpdateAmount: function () {},
    //_getInstallment: function () {},
    _enableButton: function () {},
    _onClickPaymentType: function () {},
    _onClickPaymentTypeCredit: function () {},
    _onClickPaymentTypeWallet: function () {},
    _onClickPaymentTypeTransfer: function () {},
    _onClickPaymentContactless: function () {},
});

publicWidget.registry.payloxTokenVerifyResult = publicWidget.Widget.extend({
    selector: '.payment-token-result #wrapwrap',

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            setInterval(() => {
                if (document.getElementById('success')) {
                    window.parent.document.querySelector('.o_form_payment_token_verify').closest('.modal-content').querySelector('header button.close').click();
                }
            }, 2000);
        });
    },
});

export default publicWidget.registry.payloxTokenVerify;