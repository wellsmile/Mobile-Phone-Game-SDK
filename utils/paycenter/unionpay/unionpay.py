#coding=utf-8
'''
Created on Sep 10, 2016

@author: Felix
'''
import time
import hashlib
import urllib, urllib2
import base64
import OpenSSL
from django.conf import settings

def build_sign(param_map, sign_type="RSA"):
    '''构建签名'''
    # 将筛选的参数按照第一个字符的键值ASCII码递增排序（字母升序排序），如果遇到相同字符则按照第二个字符的键值ASCII码递增排序，以此类推。
    sort_param = sorted([(key, unicode(value, settings.UNIONPAY_ENCODING).encode(settings.UNIONPAY_ENCODING)) for key, value in param_map.iteritems()], key=lambda x: x[0])
    content = '&'.join(['='.join(x) for x in sort_param])
    message = hashlib.sha1(content).hexdigest()
    return base64.b64encode(OpenSSL.crypto.sign(settings.UNIONPAY_PRIVATE_KEY_OBJ, message, 'sha1'))

def build_params(out_trade_no, total_amount):
    params = {}
    # 获取配置信息
    params['accType'] = settings.UNIONPAY_ACC_TYPE
    params['accessType'] = settings.UNIONPAY_ACCESS_TYPE
    params['backUrl'] = settings.UNIONPAY_BACK_URL
    params['frontUrl'] = settings.UNIONPAY_FRONT_URL
    params['bizType'] = settings.UNIONPAY_BIZ_TYPE
    params['certId'] = settings.UNIONPAY_CERT_ID
    params['channelType'] = settings.UNIONPAY_CHANNEL_TYPE
    params['currencyCode'] = settings.UNIONPAY_CURRENCY_CODE
    params['encoding'] = settings.UNIONPAY_ENCODING
    params['merId'] = settings.UNIONPAY_MER_ID
    params['signMethod'] = settings.UNIONPAY_SIGN_METHOD
    params['txnType'] = settings.UNIONPAY_TXN_TYPE
    params['txnSubType'] = settings.UNIONPAY_TXN_SUBTYPE
    params['version'] = settings.UNIONPAY_VERSION
    
    params['orderId'] = out_trade_no
    params['txnAmt'] = '%d' % int(total_amount) # 单位为分
    params['txnTime'] = time.strftime('%Y%m%d%H%M%S') # 
    
    params['signature'] = build_sign(params)
#     return params
    return urllib.urlencode(params)

def check_sign(message, sign):
    try:
        OpenSSL.crypto.verify(settings.UNIONPAY_PUBLIC_KEY_OBJ, sign, message, 'SHA1')
        return True
    except Exception as _:
        return False

if __name__ == '__main__':
    params = build_params('1111111111', 1)
    request_obj = urllib2.Request('https://101.231.204.80:5000/gateway/api/frontTransReq.do')
    request_obj.add_data(params)
    print(urllib2.urlopen(request_obj).read())