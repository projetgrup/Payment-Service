# -*- coding: utf-8 -*-
# Copyright © 2024 Projet (https://bulutkobi.io)
# Part of Paylox License. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment System - Agreement',
    'version': '1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'sequence': 1454,
    'category': 'Accounting/Payment Acquirers',
    'depends': [
        'payment_jetcheckout_system',
        'payment_system_product',
    ],
    'data': [
        #'views/settings.xml',
        'views/partner.xml',
        'views/agreement.xml',
        'views/transaction.xml',
        'views/templates.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_qweb': [
            'payment_system_agreement/static/src/xml/page.xml',
        ],
        'web.assets_frontend': [
            'payment_system_agreement/static/src/scss/page.scss',
            'payment_system_agreement/static/src/js/page.js',
            #'payment_system_agreement/static/src/js/flow.js', #TODO examine
        ],
    },
    'images': ['static/description/icon.png'],
}
