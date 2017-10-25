#coding=utf-8
'''
Created on 2016年11月8日

@author: xiaochengcao
'''
#coding=utf-8
import json
from api.models import ThirdPartyAppInfo, App

import requests

def get_client(appid):
    appid = str(appid)
    client = ThirdPartyAppInfo.objects.get(app__appid=appid, thirdparty='google')
    clientresult = ''
    for eachclientinfo in json.loads(client.info):
        if len(eachclientinfo['client_secret']) >= 2:
            clientresult = eachclientinfo 
            break
        if eachclientinfo.has_key('redirect_appid'):
            clientresult = get_client(eachclientinfo['redirect_appid'])
    return clientresult
    
def token_refresh(appid):
    '''
    刷新access_token，返回当前可用的access_token
    '''
    params = {}
    clientresult = get_client(appid)
    #取第一个有client_secret值的dict作为要使用的记录
    params['grant_type'] = 'refresh_token'
    params['client_id'] = clientresult['client_id']
    params['client_secret'] = clientresult['client_secret']
    params['refresh_token'] = clientresult['refresh_token']
    token_response = requests.post('https://accounts.google.com/o/oauth2/token', params)
    token_response_dict = json.loads(token_response.content)
    return token_response_dict['access_token']
    
def check_product_status(packagename, productid, token, servertoken):
    '''
    此方法查询商品购买状态，返回订单的支付状态
    Doc: https://developers.google.com/android-publisher/api-ref/purchases/products/get
    '''
    products_get_url = 'https://www.googleapis.com/androidpublisher/v2/applications/'+packagename+'/purchases/products/'+productid+'/tokens/'+token+'?access_token='+servertoken
    product_status_response = requests.get(products_get_url)
    product_status_dict = json.loads(product_status_response.content)
    return product_status_dict['purchaseState']
