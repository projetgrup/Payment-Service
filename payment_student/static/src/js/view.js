odoo.define('payment_student.StudentList', function (require) {
'use strict';

const PartnerController = require('payment_jetcheckout_system.PartnerController');
const viewRegistry = require('web.view_registry');
const ListView = require('web.ListView');
const core = require('web.core');
const _t = core._t;

const StudentListController = PartnerController.extend({
    events: _.extend({}, PartnerController.prototype.events, {
        'click .o_button_import_student': '_onClickImportStudent',
    }),

    willStart: function() {
        const ready = this.getSession().user_has_group('payment_student.group_student_manager').then((is_admin) => {
            if (is_admin) {
                this.buttons_template = 'StudentListView.buttons';
            }
        });
        return Promise.all([this._super.apply(this, arguments), ready]);
    },

    _onClickImportStudent: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'payment.student.import',
            name: _t('Import Student'),
            view_mode: 'form',
            views:[[false, 'form']],
            target: 'new',
        });
    },
});

const StudentListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: StudentListController,
    }),
});

viewRegistry.add('student_buttons', StudentListView);
});
