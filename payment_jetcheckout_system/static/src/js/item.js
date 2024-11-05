odoo.define('payment_jetcheckout_system.ItemController', function (require) {

const ListController = require('web.ListController');
const { _t } = require('web.core');

const ItemController = ListController.extend({
    events: _.extend({}, ListController.prototype.events, {'click .o_button_import_item': '_onClickImportItem'}),

    init: function () {
        this._super.apply(this, arguments);
        this.buttons_template = 'ItemListView.buttons';
    },

    _onClickImportItem: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'payment.item.import',
            name: _t('Import Items'),
            views:[[false, 'form']],
            view_mode: 'form',
            target: 'new',
        });
    }
});

return ItemController;
});

odoo.define('payment_jetcheckout_system.ItemView', function (require) {

const ItemController = require('payment_jetcheckout_system.ItemController');
const ListView = require('web.ListView');
const viewRegistry = require('web.view_registry');

const ItemView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, { Controller: ItemController })
});

viewRegistry.add('system_item', ItemView);
});