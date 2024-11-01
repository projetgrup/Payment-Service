odoo.define('payment_jetcheckout.TransactionList', function (require) {
'use strict';

const ListController = require('web.ListController');
const ListView = require('web.ListView');
const viewRegistry = require('web.view_registry');
const { _t } = require('web.core');

const TransactionListController = ListController.extend({
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_import_transaction': '_onClickImportTransaction',
    }),

    willStart: function() {
        const ready = this.getSession().user_has_group('account.group_account_manager').then((is_admin) => {
            if (is_admin) {
                this.buttons_template = 'TransactionListView.buttons';
            }
        });
        return Promise.all([this._super.apply(this, arguments), ready]);
    },

    _onClickImportTransaction: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'payment.transaction.import',
            name: _t('Import Transaction'),
            view_mode: 'form',
            views:[[false, 'form']],
            target: 'new',
        });
    },
});

const TransactionListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TransactionListController,
    }),
});

viewRegistry.add('transaction_buttons', TransactionListView);
return { TransactionListController, TransactionListView }
});
