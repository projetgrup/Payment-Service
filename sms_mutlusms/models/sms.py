# -*- coding: utf-8 -*-
import requests

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.sms_api.models.sms import InsufficientCreditError

SENDURL = 'https://smsgw.mutlucell.com/smsgw-ws/sndblkex'
CREDITURL = 'https://smsgw.mutlucell.com/smsgw-ws/gtcrdtex'
HEADERS = {'content-type': 'text/xml; charset=utf-8'}
ERRORS = {
    None: ValidationError('Bir hata meydana geldi'),
    False: ValidationError('İstek zaman aşımına uğdadı'),
    '20': ValidationError('Post edilen xml eksik veya hatalı'),
    '21': AccessError('Kullanılan originatöre sahip değilsiniz'),
    '22': InsufficientCreditError('Kontörünüz yetersiz'),
    '23': AccessError('Kullanıcı adı ya da parolanız hatalı'),
    '24': ValidationError('Şu anda size ait başka bir işlem aktif'),
    '25': ValidationError('SMSC Stopped (Bu hatayı alırsanız, işlemi 1-2 dk sonra tekrar deneyin)'),
    '30': AccessError('Hesap Aktivasyonu sağlanmamış'),
}


class SmsProvider(models.Model):
    _inherit = 'sms.provider'

    type = fields.Selection(selection_add=[('mutlusms', 'MutluSMS')], ondelete={'mutlusms': 'cascade'})


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _get_mutlusms_credit_url(self):
        return 'https://www.mutlucell.com.tr/7-tarifeler/'

    @api.model
    def _send_mutlusms_sms(self, messages, provider):
        username = provider.username
        password = provider.password
        originator = provider.originator

        blocks = [f"<mesaj><metin>{message['content']}</metin><nums>{message['number']}</nums></mesaj>" for message in messages]
        data = f"""<?xml version="1.0" encoding="UTF-8"?>
            <smspack ka="{username}" pwd="{password}" org="{originator}" charset="turkish">
                {"".join(blocks)}
            </smspack>"""

        try:
            response = requests.post(SENDURL, data=data.encode('utf-8'), headers=HEADERS, timeout=10)
            code = response.text
            if code.startswith('$'):
                return [{'res_id': message['res_id'], 'state': 'success'} for message in messages]
            else:
                raise ERRORS.get(code, ERRORS[None])
        except requests.exceptions.ConnectionError:
            raise ERRORS[False]
        except Exception as e:
            raise ValidationError(str(e))

    @api.model
    def _get_mutlusms_credit(self, provider):
        username = provider.username
        password = provider.password
        data = f"""<?xml version="1.0" encoding="UTF-8"?><smskredi ka="{username}" pwd="{password}"/>"""

        try:
            response = requests.post(CREDITURL, data=data.encode('utf-8'), headers=HEADERS, timeout=10)
            code = response.text
            if code.startswith('$'):
                return _('%s SMS credit(s) left') % int(float(code[1:]))
            else:
                raise ERRORS.get(code, ERRORS[None])
        except requests.exceptions.ConnectionError:
            raise ERRORS[False]
        except Exception as e:
            raise ValidationError(str(e))
