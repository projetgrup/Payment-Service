��    1      �  C   ,      8  I  9  ]   �  �   �  B   �  �  �    �  
   �*  	   �*     �*     �*     
+     +     +     ++      C+  	   d+     n+     }+     �+     �+     �+     �+     �+  &   �+     �+     �+     ,     ",     +,     9,     F,  '   T,     |,     �,     �,     �,     �,     �,     �,     �,     �,     �,     �,     -     -     +-  <   4-  9   q-  ;  �-  a  �.  V   I0  �   �0  ?   d1  �  �1  �  �@     oU  
   wU     �U     �U     �U  
   �U     �U     �U  (   �U     V     V     $V     8V     JV  	   ]V     gV     mV  %   �V     �V     �V     �V  	   �V     �V     �V     W  8   W     WW     _W     fW  &   �W  
   �W     �W     �W     �W     �W     �W     �W     
X     X  
   $X  K   /X  3   {X               %   -                                               )               !          $      
                        *                            '      .   #   ,   +      1         0                 "   /   	   &               (    <p>
    <strong>Dear <i t-out="object.name"/></strong>,
    <br/><br/>
    If you want to view and pay online, <a t-att-href="object._get_payment_url()" style="color:#3079ed;">click here.</a>
    <br/><br/>
    Have a nice day.
    <br/><br/>
    Sincerely...
    <br/><br/>
    <span t-out="object._get_payment_company()"/>
</p> <strong class="h4">Thank You!</strong><br/>There is not any unpaid transaction related to you <strong class="text-primary font-weight-bold z-index-1 flex-fill">Payment</strong>
                                <strong class="text-primary font-weight-bold text-right z-index-1">Amount</strong> <strong class="text-primary font-weight-bold">Information</strong> <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Hello <strong t-out="object.name or ''">Marc Demo</strong>,<br/><br/>
                        Successful transaction information as follows.<br/><br/>
                        Transaction Owner Company : <t t-esc="ctx['partner'].name or ''"/><br/>
                        Transaction Date : <t t-out="ctx['tx'].last_state_change.strftime('%d.%m.%Y %H:%M:%S')">01.01.2022 00:00:00</t><br/>
                        Transaction Amount : <t t-esc="format_amount(ctx['tx'].jetcheckout_payment_amount, ctx['tx'].currency_id) or ''"/><br/>
                        Installment Count : <t t-esc="ctx['tx'].jetcheckout_installment_description_long or ''"/><br/><br/>
                        <div style="margin: 16px 0px 16px 0px; text-align: center;">
                            <a t-att-href="'%s/report/html/payment_jetcheckout.payment_receipt/%s' % (ctx['url'], ctx['tx'].id)" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px; background-color: #875A7B; color: #fff; border-radius: 5px;">
                                <strong>Receipt</strong>
                            </a>
                            <a t-att-href="'%s/report/html/payment_jetcheckout.payment_conveyance/%s' % (ctx['url'], ctx['tx'].id)" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px; background-color: #875A7B; color: #fff; border-radius: 5px;">
                                <strong>Conveyance</strong>
                            </a>
                        </div>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="ctx['company'].name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="ctx['company'].phone or ''">+1 650-123-4567</t>
                    <t t-if="ctx['company'].email">
                        | <a t-attf-href="mailto:{{ ctx['company'].email }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="ctx['company'].website">
                        | <a t-attf-href="{{ ctx['company'].website }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table> <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="700" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 700px;">
            <table border="0" cellpadding="0" cellspacing="0" width="700" style="min-width: 700px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr>
                    <td valign="top" style="font-size: 13px;">
                        <div>
                            Hello <strong t-out="object.name or ''">Marc Demo</strong>,<br/><br/>
                        </div>
                    </td>
                </tr>
                <t t-if="ctx['total'] &gt; 0 and len(ctx['transactions']) &gt; 0">
                    <tr>
                        <td valign="top" style="font-size: 13px;">
                            <div>
                                Summary of transactions related to your company on <t t-out="ctx['date']"/> as follows.<br/><br/>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td valign="top" style="font-size: 13px; text-align: center;">
                            <table style="table-layout: fixed; width: 90%;">
                                <thead>
                                    <tr>
                                        <th style="border-bottom: 2px solid #ccc; text-align: left;">Vendor/Customer Name</th>
                                        <th style="border-bottom: 2px solid #ccc; text-align: right;">Amount of payment</th>
                                        <th style="border-bottom: 2px solid #ccc; text-align: right;">Share of payment</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <t t-foreach="ctx['transactions']" t-as="line">
                                        <tr>
                                            <td style="border-bottom: 1px solid #ccc; text-align: left;"><t t-out="line[1]['name']"/></td>
                                            <td style="border-bottom: 1px solid #ccc; text-align: right;"><t t-out="format_amount(line[1]['amount'], ctx['company'].currency_id) or ''"/></td>
                                            <td style="border-bottom: 1px solid #ccc; text-align: right;">% <t t-out="'%.2f' % round(100 * line[1]['amount']/ctx['total'], 2) if ctx['total'] != 0 else 0"/></td>
                                        </tr>
                                    </t>
                                    <tr style="font-weight:bold;">
                                        <td style="text-align: left;">Total</td>
                                        <td style="text-align: right;"><t t-out="format_amount(ctx['total'], ctx['company'].currency_id) or ''"/></td>
                                        <td style="text-align: right;">% <t t-out="'%.2f' % 100"/></td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                </t>
                <t t-else="">
                    <tr>
                        <td valign="top" style="font-size: 13px;">
                            <div>
                                There is no payment transactions related to your company on <t t-out="ctx['date']"/><br/><br/>
                            </div>
                        </td>
                    </tr>
                </t>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="ctx['company'].name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="ctx['company'].phone or ''">+1 650-123-4567</t>
                    <t t-if="ctx['company'].email">
                        | <a t-attf-href="mailto:{{ ctx['company'].email }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="ctx['company'].website">
                        | <a t-attf-href="{{ ctx['company'].website }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table> Authorized Companies Company Settings Configuration Contact Contacts Create a vendor Create a vendor contact Created payments are listed here Dashboard Email Settings Email Templates HTTP Routing Mail Servers Manager Menu No payments yet Payment - {{ object.company_id.name }} Payment Acquirers Payment Settings Payment Transaction Payments SMS Providers SMS Settings SMS Templates Send daily report email of transactions Settings System Transaction: Daily Report Transaction: Successful Email Transactions User Users VPS Vendor Vendor Payment Email Vendor Payment System Vendors Website Settings Websites {{ ctx['domain'] }} | About transaction on {{ ctx['date'] }} {{ ctx['domain'] }} | Successful Transaction Notification Project-Id-Version: Odoo Server 15.0-20220110
Report-Msgid-Bugs-To: 
PO-Revision-Date: 2022-11-03 18:40+0300
Last-Translator: 
Language-Team: 
Language: tr
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n != 1);
X-Generator: Poedit 3.1.1
 <p>
    <strong>Sayın <i t-out="object.name"/></strong>,
    <br/><br/>
    İncelemek ve Online Ödeme için <a t-att-href="object._get_payment_url()" style="color:#3079ed;">tıklayınız.</a>
    <br/><br/>
    Sağlıklı bir yıl dileriz.
    <br/><br/>
    Saygılarımızla...
    <br/><br/>
    <span t-out="object._get_payment_company()"/>
</p> <strong class="h4">Teşekkür Ederiz!</strong><br/>Size ait ödenmemiş bir işlem yok <strong class="text-primary font-weight-bold z-index-1 flex-fill">Ödeme</strong>
                                <strong class="text-primary font-weight-bold text-right z-index-1">Tutar</strong> <strong class="text-primary font-weight-bold">Bilgiler</strong> <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Merhaba <strong t-out="object.name or ''">Marc Demo</strong>,<br/><br/>
                        Başarılı işlem bilgileri aşağıdaki gibidir.<br/>
                        İşlem Geçen Firma : <t t-esc="ctx['partner'].name or ''"/><br/>
                        İşlem Tarihi : <t t-out="ctx['tx'].last_state_change.strftime('%d.%m.%Y %H:%M:%S')">01.01.2022 00:00:00</t><br/>
                        İşlem Tutarı : <t t-esc="format_amount(ctx['tx'].jetcheckout_payment_amount, ctx['tx'].currency_id) or ''"/><br/>
                        Taksit Sayısı : <t t-esc="ctx['tx'].jetcheckout_installment_description_long or ''"/><br/><br/>
                        <div style="margin: 16px 0px 16px 0px; text-align: center;">
                            <a t-att-href="'%s/report/html/payment_jetcheckout.payment_receipt/%s' % (ctx['url'], ctx['tx'].id)" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px; background-color: #875A7B; color: #fff; border-radius: 5px;">
                                <strong>Makbuz</strong>
                            </a>
                            <a t-att-href="'%s/report/html/payment_jetcheckout.payment_conveyance/%s' % (ctx['url'], ctx['tx'].id)" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px; background-color: #875A7B; color: #fff; border-radius: 5px;">
                                <strong>Temlikname</strong>
                            </a>
                        </div>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="ctx['company'].name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="ctx['company'].phone or ''">+1 650-123-4567</t>
                    <t t-if="ctx['company'].email">
                        | <a t-attf-href="mailto:{{ ctx['company'].email }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="ctx['company'].website">
                        | <a t-attf-href="{{ ctx['company'].website }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table> <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="700" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 700px;">
            <table border="0" cellpadding="0" cellspacing="0" width="700" style="min-width: 700px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr>
                    <td valign="top" style="font-size: 13px;">
                        <div>
                            Hello <strong t-out="object.name or ''">Marc Demo</strong>,<br/><br/>
                        </div>
                    </td>
                </tr>
                <t t-if="ctx['total'] &gt; 0 and len(ctx['transactions']) &gt; 0">
                    <tr>
                        <td valign="top" style="font-size: 13px;">
                            <div>
                                <t t-out="ctx['date']"/> tarihindeki işlem toplamınız aşağıdaki gibidir.<br/><br/>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td valign="top" style="font-size: 13px; text-align: center;">
                            <table style="table-layout: fixed; width: 90%;">
                                <thead>
                                    <tr>
                                        <th style="border-bottom: 2px solid #ccc; text-align: left;">Bayi/Müşteri Adı</th>
                                        <th style="border-bottom: 2px solid #ccc; text-align: right;">Tahsilat Tutarı</th>
                                        <th style="border-bottom: 2px solid #ccc; text-align: right;">Tahsilattaki Payı</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <t t-foreach="ctx['transactions']" t-as="line">
                                        <tr>
                                            <td style="border-bottom: 1px solid #ccc; text-align: left;"><t t-out="line[1]['name']"/></td>
                                            <td style="border-bottom: 1px solid #ccc; text-align: right;"><t t-out="format_amount(line[1]['amount'], ctx['company'].currency_id) or ''"/></td>
                                            <td style="border-bottom: 1px solid #ccc; text-align: right;">% <t t-out="'%.2f' % round(100 * line[1]['amount']/ctx['total'], 2) if ctx['total'] != 0 else 0"/></td>
                                        </tr>
                                    </t>
                                    <tr style="font-weight:bold;">
                                        <td style="text-align: left;">Toplam</td>
                                        <td style="text-align: right;"><t t-out="format_amount(ctx['total'], ctx['company'].currency_id) or ''"/></td>
                                        <td style="text-align: right;">% <t t-out="'%.2f' % 100"/></td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                </t>
                <t t-else="">
                    <tr>
                        <td valign="top" style="font-size: 13px;">
                            <div>
                                <t t-out="ctx['date']"/> tarihinde gerçekleşen bir işlem bulunmuyor.<br/><br/>
                            </div>
                        </td>
                    </tr>
                </t>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="ctx['company'].name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="ctx['company'].phone or ''">+1 650-123-4567</t>
                    <t t-if="ctx['company'].email">
                        | <a t-attf-href="mailto:{{ ctx['company'].email }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="ctx['company'].website">
                        | <a t-attf-href="{{ ctx['company'].website }}" style="text-decoration:none; color: #454748;" t-out="ctx['company'].website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table> Yetkili Şirketler Şirket Ayarları Yapılandırma Yetkili Yetkililer Bir bayi oluştur Bir bayi yetkilisi oluştur Oluşturulan ödemeler burada listelenir Panel Eposta Ayarları Eposta Şablonları HTTP Yönlendirme Eposta Sunucuları Yönetici Menü Henüz bir ödeme yok Ödeme - {{ object.company_id.name }} Ödeme Alıcıları Ödeme Ayarları Ödeme İşlemleri Ödemeler SMS Sağlayıcılar SMS Ayarları SMS Şablonları Ödeme işlemleri için günlük rapor epostası gönder Ayarlar Sistem Ödeme İşlemi: Günlük Rapor Ödeme İşlemi: Başarılı Epostası İşlemler Kullanıcı Kullanıcılar BTS Bayi Bayi Tahsilat Epostası Bayi Tahsilat Sistemi Bayiler Website Ayarları Websiteler {{ ctx['domain'] }} | {{ ctx['date'] }} tarihindeki işlemleriniz hakkında {{ ctx['domain'] }} | Başarılı İşlem Bildirimi 