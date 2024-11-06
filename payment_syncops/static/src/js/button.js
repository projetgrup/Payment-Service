odoo.define('payment_syncops.SyncController', function (require) {
"use strict";

const PartnerController = require('payment_jetcheckout_system.PartnerController');
const ItemController = require('payment_jetcheckout_system.ItemController');
const SyncButtonMixin = require('connector_syncops.SyncButtonMixin');

_.extend(SyncButtonMixin, {

    willStart: function() {
        const shown = this._rpc({
            model: 'syncops.connector',
            method: 'count',
            args: ['payment_get_partner_list'],
        }).then((show) => {
            this.show_button = !!show && this.show_button;
        }).guardedCatch((error) => {
            console.error(error);
        });

        const granted = this.getSession().user_has_group('payment_syncops.group_sync').then((has_group) => {
            this.show_button = has_group && this.show_button;
        });

        return Promise.all([this._super.apply(this, arguments), shown, granted]);
    },

});

PartnerController.include(_.extend({}, SyncButtonMixin, {
    events: _.extend({}, SyncButtonMixin.events, PartnerController.prototype.events),
}));

ItemController.include(_.extend({}, SyncButtonMixin, {
    events: _.extend({}, SyncButtonMixin.events, ItemController.prototype.events),
}));

});