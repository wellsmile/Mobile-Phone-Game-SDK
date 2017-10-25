#coding=utf-8
'''
Created on 2017年4月5日

@author: xiaochengcao
'''
import hashlib
import json

import requests

from django.conf import settings

def build_sign(params_dict):
    params_keys = params_dict.keys()
    params_keys.sort()
    sign_list = []
    for key in params_keys:
        if str(params_dict[key]):
            # 此处与文档不同，文档要求参数值进行encode后参与签名，实测并不对
            url_value = str(params_dict[key])
            sign_list.append('='.join( (str(key), url_value)))
    sign_list.append('key=' + '37f6b2579b3247eb38683f845c085f8a')
#     settings.FENQILEPAY_SECRET
    sign_str = '&'.join(sign_list)
    return hashlib.md5(sign_str).hexdigest().lower()

def build_params(amount, trade_id, good_name, ip, product_id):
    params = {}
    params['amount'] = amount
    params['out_trade_no'] = trade_id
    params['partner_id'] = settings.FENQILEPAY_PARTNER_ID
    params['notify_url'] = settings.FENQILEPAY_NOTIFY_URL
    params['subject'] = good_name
    params['client_ip'] = ip
    params['c_merch_id'] = settings.FENQILEPAY_C_MERCH_ID
    params['payment_type'] = 2
    params['attach'] = product_id
    
    params['sign'] = build_sign(params)
    return json.dumps(params)

def build_resp(params):
    resp = requests.post(settings.FENQILEPAY_DOPAY_URL, params)
    resp_dict = json.loads(resp.content)
    return resp_dict
    
