# -*- coding: utf-8 -*-
# Copyright © 2024 Projet (https://bulutkobi.io)
# Part of Paylox License. See LICENSE file for full copyright and licensing details.
# Set nginx settings to 'proxy_cookie_path / "/; secure; SameSite=none";'

{
    'name': 'Paylox Payment Acquirer',
    'version': '1.11',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'sequence': 1453,
    'category': 'Accounting/Payment Acquirers',
    'depends': ['account_payment', 'website_payment'],
    'data': [
        'views/acquirer.xml',
        'views/transaction.xml',
        'views/partner.xml',
        'views/product.xml',
        'views/report.xml',
        'views/templates.xml',
        'wizards/signin.xml',
        'wizards/application.xml',
        'wizards/pos.xml',
        'wizards/campaign.xml',
        'wizards/transaction_import.xml',
        'report/report.xml',
        'data/data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_jetcheckout/static/src/lib/imask.js',
            'payment_jetcheckout/static/src/scss/payment.scss',
            'payment_jetcheckout/static/src/xml/templates.xml',
            'payment_jetcheckout/static/src/js/tools.js',
            'payment_jetcheckout/static/src/js/cards.js',
            'payment_jetcheckout/static/src/js/framework.js',
            'payment_jetcheckout/static/src/js/form.js',
            'payment_jetcheckout/static/src/js/fields.js',
            'payment_jetcheckout/static/src/js/page.js',
            'payment_jetcheckout/static/src/js/token.js',
        ],
        'web.assets_backend': [
            'payment_jetcheckout/static/src/scss/backend.scss',
            'payment_jetcheckout/static/src/js/backend.js',
            'payment_jetcheckout/static/src/js/transaction.js',
        ],
        'web.assets_qweb': [
            'payment_jetcheckout/static/src/xml/transaction.xml',
        ],
    },
    'application': False,
    'uninstall_hook': 'uninstall_hook',
    'images': ['static/description/icon.png'],
}
