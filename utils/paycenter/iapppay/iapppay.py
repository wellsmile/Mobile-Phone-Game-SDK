#coding=utf-8
'''
Created on 2016年12月22日

@author: xiaochengcao
'''
import json
import OpenSSL
import requests
import base64
import urllib
import urlparse
from django.conf import settings

def build_sign(data):
    '''组建签名'''
    sslobj = settings.IAPPPAY_PRIVATE_KEY_OBJ
    req_sign = OpenSSL.crypto.sign(sslobj, data, 'md5')
    sign_encode = base64.encodestring(req_sign)[:-1]
    return sign_encode

def build_params(waresid, cporderid, appuserid, cpprivateinfo, price, waresname, currency='RMB'):
    '''组建dopay参数'''
    params_dict = {}
    result_dict = {}
    params_dict['appid'] = str(settings.IAPPPAY_APP_ID)
    params_dict['waresid'] = int(waresid)
    params_dict['cporderid'] = str(cporderid)
    params_dict['currency'] = str(currency)
    params_dict['appuserid'] = str(appuserid)
    params_dict['cpprivateinfo'] = str(cpprivateinfo)
    params_dict['notifyurl'] = str(settings.IAPPPAY_NOTIFY_URL)
    params_dict['price'] = float(price)/100
    params_dict['waresname'] = str(waresname)
    
    result_dict['transdata'] = json.dumps(params_dict, separators=(',',':'), ensure_ascii=False)
    result_dict['sign'] = build_sign(result_dict['transdata'])
    result_dict['signtype'] = 'RSA'
    
    result_str = urllib.urlencode(result_dict)
    return result_str
    
def check_sign(message, sign):
    '''公钥验签'''
    try:
        OpenSSL.crypto.verify(settings.IAPPPAY_PUBLIC_KEY_OBJ, sign, message, 'md5')
        return True
    except Exception as e:
        print('exception:' + str(e))
        return False

def get_dopay_resp(requestmsg):
    '''请求爱贝发起支付的接口并获取返回数据'''
    dopay_resp = requests.post(settings.IAPPPAY_DOPAY_URL, requestmsg)
    resp_dict = parse_resp(dopay_resp.content)
    transdata = json.loads(resp_dict['transdata'])
    return transdata

def parse_resp(resp_str_quota):
    '''解析爱贝的response content和回调发来的request body'''
    resp_dict = dict(urlparse.parse_qsl(resp_str_quota))
    return resp_dict

