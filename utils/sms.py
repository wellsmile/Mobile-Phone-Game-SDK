#coding=utf-8
'''
Created on Aug 27, 2016

@author: Felix
'''
import logging
import json

import top.api
from top.api.base import TopException
from django.conf import settings

sms_logger = logging.getLogger('sms')

class AliDayuSMS(object):
    @classmethod
    def send(cls, code, product, phone, sms_free_sign_name = '大鱼测试', sms_template_code = 'SMS_13700757'):
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(settings.SMS_ALIDAYU_APPKEY, settings.SMS_ALIDAYU_APPSECRET))
        req.extend = ''
        req.sms_type = 'normal'
        req.sms_free_sign_name = sms_free_sign_name
        req.sms_template_code = sms_template_code
        
        req.rec_num = phone
        req.sms_param = json.dumps({'code': code, 'product': product})
        try:
            response = req.getResponse()
            return int(response["alibaba_aliqin_fc_sms_num_send_response"]['result']['err_code']), response
        except TopException as e:
            sms_logger.error(str(e))
            return e.errorcode, e.submsg

if __name__ == '__main__':
    AliDayuSMS.send('11111', u'测试服务', '15210417809')