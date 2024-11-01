/** @odoo-module alias=paylox.system.vendor **/
'use strict';

import core from 'web.core';
import publicWidget from 'web.public.widget';
import systemPage from 'paylox.system.page';
import systemFlow from 'paylox.system.page.flow';
import fields from 'paylox.fields';

const _t = core._t;

systemFlow.dynamic.include({
    init: function() {
        this._super.apply(this, arguments);
        Object.assign(this.wizard.register, {
            country_id: new fields.integer(),
            company_type: new fields.string(),
            tax_office: new fields.string(),
            state_id: new fields.selection(),
            city: new fields.string(),
            street: new fields.string(),
            buttons: {
                company_type: new fields.element({
                    events: [['click', this._onClickCompanyType]],
                }),
            }
        });
    },

    _queryPartnerPostprocess: function (partner) {
        this._super(partner);
        if (this.system.value === 'vendor') {
            $('.payment-page span[name=country]').text(Array.isArray(partner.country_id) ? partner.country_id[1] : partner.country_id || '-');
            $('.payment-page span[name=state]').text(Array.isArray(partner.state_id) ? partner.state_id[1].replace(/\s\((.*)\)$/, '') : partner.state_id || '-');
            $('.payment-page span[name=city]').text(partner.city || '-');
            $('.payment-page span[name=street]').text(partner.street || '-');
            $('.payment-page span[name=phone]').text(partner.phone || '-');
            $('.payment-page span[name=email]').text(partner.email || '-');
        }
    },

    _onClickCompanyType: function(ev) {
        const button = $(ev.currentTarget);
        const buttons = $('.payment-page button[field="wizard.register.buttons.company_type"]');
        buttons.removeClass('selected').find('input').prop({'checked': false});
        button.addClass('selected').find('input').prop({'checked': true});

        const type = button.attr('name');
        this.wizard.register.company_type.value = type;

        const name = this.wizard.register.name.$.parent().find('label span');
        const vat = this.wizard.register.vat.$.parent().find('label span');
        const office = this.wizard.register.tax_office;
        if (type === 'company') {
            name.text(_t('Company Name'));
            vat.text(_t('VAT'));
            office.$.parent().removeClass('d-none');
        } else {
            name.text(_t('Name'));
            vat.text(_t('Vat'));
            office.value = '';
            office.$.parent().addClass('d-none');
        }
    },

    _highlightWizardRegisterFields: function() {
        this._super.apply(this, arguments);
        this.wizard.register.tax_office.$.addClass('border-danger').siblings('label').addClass('text-danger');
    },

    _clearWizardRegisterFields: function() {
        this._super.apply(this, arguments);
        this.wizard.register.tax_office.$.removeClass('border-danger').siblings('label').removeClass('text-danger');
    },
});

publicWidget.registry.payloxSystemVendor = systemPage.extend({
    selector: '.payment-vendor #wrapwrap',
});
