#coding=utf-8
'''
Created on 2016年12月5日

@author: xiaochengcao
'''
from hashlib import sha1
import hmac
import urllib
import base64
import time
import json
import string

from django.conf import settings

def build_sign(param_map, method, urlpath):
    '''
    Doc: http://wiki.open.qq.com/wiki/腾讯开放平台第三方应用签名参数sig的说明
    '''
    appkey_ssl = settings.TENCENTPAY_APP_KEY + '&'
    code_urlpath = urllib.quote(urlpath, safe = '-_、.')
    sort_param = sorted([(key, value) for key, value in param_map.iteritems()], key=lambda x: x[0])
    content_nokey = '&'.join(['='.join(x) for x in sort_param])
    code_content = urllib.quote(content_nokey, safe = '-_、.')
    content = '&'.join([method, code_urlpath, code_content])
    sign_sha1 = hmac.new(appkey_ssl, content, sha1).digest()
    sign = base64.encodestring(sign_sha1)
    return sign.strip()

def build_params(openid, openkey, pf, pfkey, good_name, amount, goodurl, app_metadata):
    params = {}
    #公共参数
    params['openid'] = openid
    params['openkey'] = openkey
    params['appid'] = settings.TENCENTPAY_APP_ID
    params['pf'] = pf
    #私有参数
    params['ts'] = str(int(time.time()))
    params['payitem'] = '{}*{}*{}'.format(good_name, amount, '1')
    params['goodsmeta'] = '{}*{}'.format(good_name, good_name)
    params['goodsurl'] = goodurl
    params['zoneid'] = '0'
    params['pfkey'] = pfkey
    params['app_metadata'] = app_metadata
    #构建签名
    params['sig'] = build_sign(params, 'POST', '/v3/pay/buy_goods')
    return params

def check_sign(params_json):
    '''http://wiki.open.qq.com/wiki/mobile/购买道具扣款成功回调应用发货'''
    def build_notify_sign(param_map, method, urlpath):
        appkey_ssl = settings.TENCENTPAY_APP_KEY + '&'
        code_urlpath = urllib.quote(urlpath, safe = '-_、.')
        param_map_ascii = change_ascii(param_map) # 回调签名验证时多加的一步
        sort_param = sorted([(key, value) for key, value in param_map_ascii.iteritems()], key=lambda x: x[0])
        content_nokey = '&'.join(['='.join(x) for x in sort_param])
        code_content = urllib.quote(content_nokey, safe = '-_、.')
        content = '&'.join([method, code_urlpath, code_content])
        sign_sha1 = hmac.new(appkey_ssl, content, sha1).digest()
        sign = base64.encodestring(sign_sha1)
        return sign.strip()
    
    def change_ascii(params_dict):
        result_dict = {}
        nocode_str = string.letters + string.digits + '!*()'
        for param_key in params_dict.keys():
            i = 0
            param_value_list = list(params_dict[param_key])
            for param_char in param_value_list:
                if param_char not in nocode_str:
                    param_value_list[i] = str(ord(param_char))
                i=i+1
            result_dict[param_key] = ''.join(param_value_list)
        return result_dict
                    
    params_dict = json.loads(params_json)
    if params_dict.has_key('sig'):
        sign = params_dict.pop('sig')
        return (sign == build_notify_sign(params_dict))
    else:
        return False