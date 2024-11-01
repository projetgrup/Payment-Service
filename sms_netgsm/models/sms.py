# -*- coding: utf-8 -*-
import ast
import requests
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

SENDURL = 'https://api.netgsm.com.tr/sms/send/xml'
OTPSENDURL = 'https://api.netgsm.com.tr/sms/send/otp'
CREDITURL = 'https://api.netgsm.com.tr/balance'
REPORTURL = 'https://api.netgsm.com.tr/sms/report'
HEADERS = {'Content-Type': 'application/xml'}
ERRORS = {
    None: ValidationError('Bir hata meydana geldi'),
    '20': UserError('Mesaj metni hatalı veya standart maksimum mesaj sayısını aşıyor'),
    '30': AccessError('Geçersiz kullanıcı adı veya şifre'),
    '40': ValidationError('Kullanılan başlık sistemde tanımlı değil'),
    '50': ValidationError('Abone hesabı ile İYS kontrollü gönderimler yapılamaz'),
    '51': ValidationError('Aboneliğinize tanımlı İYS marka bilgisi bulunamadı'),
    '60': ValidationError('Kayıt Bulunamadı'),
    '70': ValidationError('Hatalı sorgulama'),
    '80': ValidationError('Gönderim sınır aşımı'),
    '85': ValidationError('Mükerrer Gönderim sınır aşımı'),
    '100': ValidationError('Sistem hatası'),
    '101': ValidationError('Sistem hatası'),
}


class SmsProvider(models.Model):
    _inherit = 'sms.provider'

    type = fields.Selection(selection_add=[('netgsm', 'Netgsm')], ondelete={'netgsm': 'cascade'})


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _get_netgsm_credit_url(self):
        return 'https://www.netgsm.com.tr/fiyatlar/'

    @api.model
    def _process_netgsm_sms(self, text):
        if ' ' in text:
            return text.split(' ')
        return text, '0'

    @api.model
    def _send_netgsm_sms(self, messages, provider):
        username = provider.username
        password = provider.password
        originator = provider.originator

        if self.env.context.get('otp'):
            # when sending otp messages, manipulate numbers with removing country code and spaces
            url = OTPSENDURL
            blocks = [f"<msg>{message['content']}</msg><no>{message['number'].replace(' ','')[-10:]}</no>" for message in messages]
            data = f"""<?xml version="1.0" encoding="UTF-8"?>
                <mainbody>
                    <header>    
                        <usercode>{username}</usercode>
                        <password>{password}</password>
                        <msgheader>{originator}</msgheader>
                    </header>
                    <body>
                        {"".join(blocks)}
                    </body>
                </mainbody>"""
        else:
            url = SENDURL
            blocks = [f"<mp><msg><![CDATA[{message['content']}]]></msg><no>{message['number']}</no></mp>" for message in messages]
            data = f"""<?xml version="1.0" encoding="UTF-8"?>
                <mainbody>
                    <header>
                        <company dil="TR">Netgsm</company>       
                        <usercode>{username}</usercode>
                        <password>{password}</password>
                        <type>n:n</type>
                        <filter>0</filter>
                        <msgheader>{originator}</msgheader>
                    </header>
                    <body>
                        {"".join(blocks)}
                    </body>
                </mainbody>"""

        response = requests.post(url, data=data.encode('utf-8'), headers=HEADERS)
        code, id, *args = self._process_netgsm_sms(response.text)
        if code.startswith('0'):
            return [{'res_id': message['res_id'], 'state': 'success'} for message in messages]
        else:
            if self.env.context.get('otp'):
                return [{'res_id': message['res_id'], 'state': 'success'} for message in messages]
            elif self.env.context.get('no_exception'):
                return []
            else:
                raise ERRORS.get(code, ERRORS[None])

    @api.model
    def _get_netgsm_credit(self, provider):
        username = provider.username
        password = provider.password
        data = f"""<?xml version='1.0'?>
            <mainbody>
                <header>
                    <usercode>{username}</usercode>
                    <password>{password}</password>
                    <stip>1</stip>
                    <view>1</view>
                </header>
            </mainbody>"""

        response = requests.post(CREDITURL, data=data.encode('utf-8'), headers=HEADERS)
        result = etree.fromstring(response.text)
        credit = result.xpath('//balance_name[text()="Adet SMS"]/../amount')
        if credit:
            credit = credit[0].text
            try:
                credit = float(credit)
            except:
                credit = credit.replace('.','').replace(',','.')
                credit = ast.literal_eval(credit)
            return _('%s SMS credit(s) left') % int(credit)
        else:
            raise ERRORS.get('30', ERRORS[None])
