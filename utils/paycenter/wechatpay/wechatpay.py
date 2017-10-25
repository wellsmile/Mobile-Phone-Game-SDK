#coding=utf-8
'''
Created on 2016年10月12日

@author: xiaochengcao
'''
import hashlib
import string
from random import sample
import time
import json
import xml.dom.minidom
import xml.sax.handler
from io import BytesIO

from api.models import AppPayInfo

import requests

from django.conf import settings

class AppPayInfoNotExist(Exception):
    pass

class XMLHandler(xml.sax.handler.ContentHandler): 
    def __init__(self): 
        self.buffer = ""                   
        self.mapping = {}                 
 
    def startElement(self, name, attributes): 
        self.buffer = ""                   
 
    def characters(self, data): 
        self.buffer += data                     
 
    def endElement(self, name): 
        self.mapping[name] = self.buffer          
 
    def getDict(self): 
        return self.mapping

def build_sign(appid, wx_appid, param_map):
    '''
        传入appid和微信id，取数据库中对应的参数构建签名
    Doc: https://pay.weixin.qq.com/wiki/doc/api/app/app.php?chapter=4_3
    '''
#设所有发送或者接收到的数据为集合M，将集合M内非空参数值的参数按照参数名ASCII码从小到大排序（字典序），使用URL键值对的格式（即key1=value1&key2=value2…）拼接成字符串stringA。 
#在stringA最后拼接上key得到stringSignTemp字符串，并对stringSignTemp进行MD5运算，再将得到的字符串所有字符转换为大写，得到sign值signValue。
    apppayinfo = AppPayInfo.objects.get(app__appid=appid, paytype='wechatpay')
    appkey = json.loads(apppayinfo.info)[wx_appid]['appkey']
    Nonevalue_keys = []
    for key in param_map.keys():
        if not param_map[key]:
            Nonevalue_keys.append(key)
    for Nonekey in Nonevalue_keys:
        param_map.pop(Nonekey)
    sort_param = sorted([(key, value) for key, value in param_map.iteritems()], key=lambda x: x[0])
    content_nokey = '&'.join(['='.join(x) for x in sort_param])
    content = '&'.join([content_nokey, 'key=' + appkey])
    return hashlib.md5(content).hexdigest().upper()

def build_xml(param_dict):
    '''将param_dict转为xml格式并返回字符串'''
    xml_doc = xml.dom.minidom.Document()
    xml_rootnode = xml_doc.createElement('xml')
    xml_doc.appendChild(xml_rootnode)
    for param_dict_key in param_dict.keys():
        nodename = xml_doc.createElement(param_dict_key)
        nodename.appendChild(xml_doc.createTextNode(param_dict[param_dict_key]))
        xml_rootnode.appendChild(nodename)
    tmp_writer = BytesIO()
    xml_doc.writexml(tmp_writer, newl='\n', encoding="utf-8")
    #indent='\t', addindent='\t', newl='\n', 
    return str(tmp_writer.getvalue())

def parse_xml(param_xml):
    '''将param_xml转为dict并返回字典'''
    params_XMLhandler = XMLHandler() 
    xml.sax.parseString(param_xml, params_XMLhandler) 
    param_dict = params_XMLhandler.getDict()
    if param_dict.has_key('xml'):
        param_dict.pop('xml')
    return param_dict
    
def build_params(productid, appid, wx_appid, body, out_trade_no, total_fee, spbill_create_ip):
    '''
            相当于时序图第4步
    Doc: https://pay.weixin.qq.com/wiki/doc/api/app/app.php?chapter=9_1#
    '''
    try:
        apppayinfo = AppPayInfo.objects.get(app__appid=appid, paytype='wechatpay')
        mch_id = json.loads(apppayinfo.info)[wx_appid]['mch_id']
    except Exception:
        raise AppPayInfoNotExist
    else:
        
        params = {}
        # 获取配置文件
        params['appid']         = str(wx_appid)
        params['mch_id']        = str(mch_id)
        params['nonce_str']     = build_nonce_str()#32位 大写字母与数字的组合
        params['notify_url']    = settings.WECHATPAY_NOTIFY_URL
        params['trade_type']    = 'APP'
        params['attach']        = json.dumps({'appid': appid, 'productid': productid})
        # 业务参数
        params['body']               = body#商品描述交易字段格式:腾讯充值中心-QQ会员充值
        params['out_trade_no']       = out_trade_no#商户系统内部的订单号,32个字符内、可包含字母
        params['total_fee']          = total_fee#订单总金额，单位为分
        params['spbill_create_ip']   = spbill_create_ip#用户端实际ip
        
        params['sign'] = build_sign(appid, wx_appid, params)#签名,至此param组装完毕
        params_xml = build_xml(params)
        return params_xml

def build_resp(appid, params_xml):
    '''向微信统一下单api发送post请求，传params_xml，并按照调起支付API组织参数返回给前端'''
    response_wechatapi = requests.post(settings.WECHATPAY_DOPAY_URL, params_xml)
    response_wechatapi_dict = parse_xml(response_wechatapi.content)
    params = {}
    params['appid'] = response_wechatapi_dict['appid']
    params['partnerid'] = response_wechatapi_dict['mch_id']
    params['prepayid'] = response_wechatapi_dict['prepay_id']
    params['package'] = 'Sign=WXPay'
    params['noncestr'] = build_nonce_str()
    params['timestamp'] = str(int(time.time()) + 28800)
    params['sign'] = build_sign(appid, params['appid'], params)
    return params

def check_sign(params_xml):
    '''检查收到的回调的return_code和签名'''
    params_dict = parse_xml(params_xml)
    return_code = params_dict['return_code']
    wx_appid = params_dict['appid']
    appid = json.loads(params_dict['attach'])['appid']
    if params_dict.has_key('sign') and return_code == 'SUCCESS':
        sign = params_dict.pop('sign')
        return (sign == build_sign(appid, wx_appid, params_dict))
    else:
        return False

def build_nonce_str():
    '''构建32位包含数字与大写字母的随机字符串'''
    return ''.join(sample(string.upper(string.letters)+string.digits,32))
