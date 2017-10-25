#coding=utf-8
'''
Created on 2017年2月27日

@author: xiaochengcao
'''
import hashlib
import json

import requests

from django.conf import settings

from api.models import AppPayInfo

class AppPayInfoNotExist(Exception):
    pass

def build_sign(appid, mol_appid, paramsdict):
    '''组建签名'''
    try:
        apppayinfo = AppPayInfo.objects.get(app__appid=appid, paytype='molpay')
        secretkey = json.loads(apppayinfo.info)[mol_appid]['secretkey']
    except Exception:
        raise AppPayInfoNotExist
    else:
        paramskeys = paramsdict.keys()
        paramskeys.sort()
        valuesstr = ''
        for paramkey in paramskeys:
            paramvalue = paramsdict.get(paramkey, None)
            if paramvalue:
                valuesstr += paramvalue
        resultstr = valuesstr + secretkey
        md5str = hashlib.md5(resultstr).hexdigest()
        return md5str

def build_params(appid, mol_appid, orderid, amount, currency, userid, **kwargs):
    '''组建dopay的参数'''
    params = {}
    
    productdes = kwargs.get('description',None)
    if productdes:
        params['description'] = productdes
    
    params['applicationCode'] = mol_appid
    params['referenceId'] = str(orderid)
    params['version'] = settings.MOLPAY_VERSION
    params['amount'] = str(amount)
    params['currencyCode'] = str(currency)
    params['returnUrl'] = settings.MOLPAY_NOTIFY_URL
    params['customerId'] = str(userid)
    params['signature'] = build_sign(appid, mol_appid, params)
    return params

def build_resp(paramsdict):
    '''dopay请求mol服务器，获取支付参数'''
    resp = requests.post(settings.MOLPAY_DOPAY_URL, paramsdict)
    respdict = json.loads(resp.content)
    paymentid = respdict.get('paymentId', None)
    paymenturl = respdict.get('paymentUrl', None)
    return paymentid, paymenturl

def check_order(appid, mol_appid, orderid, paymentid):
    '''查单，用于接收到回调后，防止是恶意仿造的回调'''
    params = {}
    params['applicationCode'] = mol_appid
    params['referenceId'] = str(orderid)
    params['paymentId'] = paymentid
    params['version'] = settings.MOLPAY_VERSION
    params['signature'] = build_sign(appid, mol_appid, params)
    resp = requests.get(settings.MOLPAY_CHECKORDER_URL, params)
    resp_dict = json.loads(resp.content)
    result_code = resp_dict.get('paymentStatusCode', None)
    return result_code