#coding=utf-8
'''
Created on Aug 31, 2016

@author: Felix
'''
import OpenSSL
import json
import time
import urllib
import base64

from django.conf import settings

def build_sign(param_map, sign_type="RSA"):
    '''
    Doc: https://doc.open.alipay.com/doc2/detail.htm?treeId=200&articleId=105351&docType=1
    '''
    # 将筛选的参数按照第一个字符的键值ASCII码递增排序（字母升序排序），如果遇到相同字符则按照第二个字符的键值ASCII码递增排序，以此类推。
    sort_param = sorted([(key, unicode(value, settings.ALIPAY_CHARSET).encode(settings.ALIPAY_CHARSET)) for key, value in param_map.iteritems()], key=lambda x: x[0])
    # 将排序后的参数与其对应值，组合成“参数=参数值”的格式，并且把这些参数用&字符连接起来，此时生成的字符串为待签名字符串。SDK中已封装签名方法，开发者可直接调用，详见SDK说明。
    # 如自己开发，则需将待签名字符串和私钥放入SHA1 RSA算法中得出签名（sign）的值。
    content = '&'.join(['='.join(x) for x in sort_param])
    return base64.encodestring(OpenSSL.crypto.sign(settings.ALIPAY_APP_PRIVATE_KEY_OBJ, content, 'sha1'))

def build_params(out_trade_no, subject, body, total_amount):
    '''
    Doc：https://doc.open.alipay.com/docs/doc.htm?spm=a219a.7629140.0.0.MVkRGo&treeId=193&articleId=105465&docType=1
    将参数按照支付宝规定组织并签名之后，返回
    '''
    params = {}
    # 获取配置文件
    params['app_id']            = settings.ALIPAY_APPID
    params['method']            = settings.ALIPAY_METHOD
    params['format']            = settings.ALIPAY_FORMAT
    params['charset']           = settings.ALIPAY_CHARSET
    params['sign_type']         = settings.ALIPAY_SIGN_TYPE
    params['sign_type']         = settings.ALIPAY_SIGN_TYPE
    params['timestamp']         = time.strftime('%Y-%m-%d %H:%M:%S')
    params['version']           = settings.ALIPAY_VERSION
    params['notify_url']        = settings.ALIPAY_NOTIFY_URL
    
    # 业务参数
    params['biz_content'] = {}
    params['biz_content']['body']              = body           # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
    params['biz_content']['subject']           = subject        # 商品的标题/交易标题/订单标题/订单关键字等。
    params['biz_content']['out_trade_no']      = out_trade_no   # 商户网站唯一订单号    
    params['biz_content']['total_amount']      = '%.2f' % (float(total_amount) / 100)   # 订单总金额，单位为元，精确到小数点后两位，取值范围[0.01,100000000]    
    params['biz_content']['product_code']      = settings.ALIPAY_APP_PRODUCT_CODE
    params['biz_content']                      = json.dumps(params['biz_content'], separators=(',', ':'))
    
    params['sign'] = build_sign(params)
    
    return urllib.urlencode(params)

def check_sign(message, sign):
    '''Doc: https://doc.open.alipay.com/docs/doc.htm?spm=a219a.7629140.0.0.dDRpeK&treeId=204&articleId=105301&docType=1'''
    try:
        OpenSSL.crypto.verify(settings.ALIPAY_PUBLIC_KEY_OBJ, sign, message, 'SHA1')
        return True
    except Exception as _:
        return False

if __name__ == '__main__':
    from operator import itemgetter
    import urlparse
    
    data = '''notify_id=f7265f7a800237cdddbff032f51e087lv6&gmt_payment=2016-09-01+20%3A45%3A58&notify_type=trade_status_sync&sign=NzhxB1E9tdEnqxR3o8pKsS1Zi4IaKEuqgZSzJn68hSY3ihpe7eIHwXWpdrJU6kYRhmw8GpLpJhsfCKnsy2teAfMlzkryZ%2F%2BrCyHjxvI1sbNOMoFcEPbPL5fp6QM8AGWUKySG%2BPywYvni9FLoqlhjVZRqhWBnfOZabqGAYRpmYrQ%3D&trade_no=2016090121001004760262317886&buyer_id=2088502975858760&app_id=2016090101834820&gmt_create=2016-09-01+20%3A45%3A58&out_trade_no=c1944e07a0c945c0a0af54ffe2918e0f&seller_id=2088421211299720&notify_time=2016-09-01+22%3A09%3A12&subject=%E7%95%AA%E8%8C%84%E9%94%A4&trade_status=TRADE_SUCCESS&total_amount=0.01&sign_type=RSA'''
    sign = 'NzhxB1E9tdEnqxR3o8pKsS1Zi4IaKEuqgZSzJn68hSY3ihpe7eIHwXWpdrJU6kYRhmw8GpLpJhsfCKnsy2teAfMlzkryZ/+rCyHjxvI1sbNOMoFcEPbPL5fp6QM8AGWUKySG+PywYvni9FLoqlhjVZRqhWBnfOZabqGAYRpmYrQ='
    d1 = [(item[0], str(item[1])) for item in urlparse.parse_qsl(data) if item[0] not in ['sign', 'sign_type']]
    getter = itemgetter(0)
    d2 = sorted([item for item in urlparse.parse_qsl(data) if item[0] not in ['sign', 'sign_type']], key=getter)
    d3 = '&'.join(['='.join(item) for item in d2])
    print(check_sign(d3, base64.decodestring(sign)))
    
    OpenSSL.crypto.verify(settings.ALIPAY_PUBLIC_KEY_OBJ, base64.decodestring(sign), d3, 'sha1')
    a = base64.encodestring(OpenSSL.crypto.sign(settings.ALIPAY_APP_PRIVATE_KEY_OBJ, d3, 'SHA1'))    