/** @odoo-module alias=paylox.system.otp.page **/
'use strict';

import config from 'web.config';
import core from 'web.core';
import rpc from 'web.rpc';
import publicWidget from 'web.public.widget';
import framework from 'paylox.framework';
import payloxPage from 'paylox.page';
import fields from 'paylox.fields';

const _t = core._t;

publicWidget.registry.PayloxSystemOtp = publicWidget.Widget.extend({
    selector: '.oe_otp_form',

    init: function (parent, options) {
        this._super(parent, options);
        this.page = 0;
        this.duration = 0;
        this.interval = undefined;
        this.next = new fields.element({
            events: [['click', this._onSend]],
        });
        this.previous = new fields.element({
            events: [['click', this._onPrevious]],
        });
        this.submit = new fields.element({
            events: [['click', this._onSubmit]],
        });
        this.resend = new fields.element({
            events: [['click', this._onResend]],
        });
        this.code = new fields.string({
            events: [['change', this._onChangeCode], ['keyup', this._onKeyupSubmit]],
        });
        this.login = new fields.string({
            events: [['keyup', this._onKeyupLogin]],
        });
        this.payment = {
            company: new fields.element({
                events: [['click', this._onClickCompany]],
            }),
        };
        this.card0 = new fields.element();
        this.card1 = new fields.element();
        this.id = new fields.string();
        this.email = new fields.string();
        this.phone = new fields.string();
        this.vat = new fields.string();
        this.ref = new fields.string();
        this.countdown = new fields.string();
    },

    start: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            payloxPage.prototype._start.apply(self);
        });
    },

    _onClickCompany: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const $button = $(ev.currentTarget);
        const cid = $button.data('id');
        rpc.query({route: '/otp/company', params: { cid }}).then(function (confirmed) {
            if (confirmed) {
                framework.showLoading();
                window.location.reload();
            }
        });
    },

    _onPrevious: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        window.location.reload();
    },

    _onSend: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (!this.login.value) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Please enter your email address or phone number or reference code'),
            });
            this.login.$.focus();
            return;
        }

        if (this.login.value.search(/\W/) >= 0) {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('Only alphanumeric characters are allowed'),
            });
            this.login.$.focus();
            return;
        }

        framework.showLoading();
        const self = this;
        rpc.query({
            route: '/otp/prepare',
            params: this._getParams(),
        }).then(function (result) {
            if (result.error) {
                self.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: result.error,
                });
            } else {
                self.duration = 120;
                self.previous.$.removeClass('d-none');
                self.submit.$.removeClass('d-none');
                self.resend.$.addClass('d-none');
                self.countdown.$.html(self.duration + ' ' + _t('seconds'));
                self.interval = setInterval(function() {
                    if (self.duration === 0) {
                        clearInterval(self.interval);
                        self.countdown.html = _t('expired');
                        self.submit.$.addClass('d-none');
                        self.resend.$.addClass('d-none');
                        return;
                    }
                    self.duration -= 1;
                    self.countdown.html = self.duration + ' ' + _t('seconds');
                }, 1000);
                self.id.value = result.id;
                self.email.html = result.email;
                self.phone.html = result.phone;
                self.vat.html = result.vat;
                self.ref.html = result.ref;
                if (self.page !== 1) {
                    self.page = 1;
                    self.next.$.addClass('d-none');
                    self.submit.$.removeClass('d-none');
                    self.card0.$.addClass('fly-left');
                    self.card1.$.removeClass('fly-right');
                }
            }
            framework.hideLoading();
        }).guardedCatch(function (error) {
            self.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please contact with your system administrator.'),
            });
            if (config.isDebug()) {
                console.error(error);
            }
            framework.hideLoading();
        });
    },

    _onResend: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (this.duration <= 0) {
            this._onSend(ev);
        }
    },

    _onSubmit: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        
        const codeRegex = /^[0-9]\d{3}$/;
        if (!codeRegex.test(this.code.value)) {
            this.displayNotification({
                type: 'warning',
                title: _t('Warning'),
                message: _t('Code must be 4 digits'),
            });
            this.code.$.focus();
            return;
        }

        const self = this;
        framework.showLoading();
        rpc.query({
            route: '/otp/validate',
            params: this._getParams(),
        }).then(function (result) {
            if ('error' in result) {
                self.displayNotification({
                    type: 'warning',
                    title: _t('Warning'),
                    message: result.error,
                });
                framework.hideLoading();
                self.code.$.focus();
            } else {
                window.location = result.url;
            }
        }).guardedCatch(function (error) {
            self.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: _t('An error occured. Please contact with your system administrator.'),
            });
            if (config.isDebug()) {
                console.error(error);
            }
            framework.hideLoading();
        });
    },

    _onChangeCode: function (ev) {
        $(ev.target).removeClass('border-danger');
        const $label = $('label[for=code]');
        $label.removeClass('text-danger');
    },

    _onKeyupCode: function (ev) {
        if (ev.key === 'Enter') {
            this._onSubmit(ev);
        }
    },

    _onKeyupLogin: function (ev) {
        if (ev.key === 'Enter') {
            this._onSend(ev);
        }
    },

    _onKeyupSubmit: function (ev) {
        if (ev.key === 'Enter') {
            this._onSubmit(ev);
        }
    },

    _getParams: function () {
        return {
            login: this.login.value,
            code: this.code.value,
            id: this.id.value,
        }
    },
});