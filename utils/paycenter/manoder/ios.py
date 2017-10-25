#coding=utf-8
'''
Created on Oct 24, 2016

@author: Felix
'''

import time
import json
import uuid
import urlparse
import urllib
import urllib2

from django.conf import settings
from api.models import User, App, UserGameOrder
from utils.signature import get_signature
from utils.paycenter.callback.callback import get_callback_arg_tuples

def budan(appid, app_order_id, amount, real_amount, good_name, pay_channel='99'):
    user = User.objects.get(username='innerbudanuser')
    app = App.objects.get(appid=appid)
    orders = UserGameOrder.objects.filter(game_order_id=app_order_id)
    if not orders.exists():
        platform = 2
        passthrough = ''
        game_callback_url = ''
        order = UserGameOrder.create_order(
                    user=user, real_amount=real_amount, currency='cny', 
                    app=app, game_order_id=app_order_id,
                    amount=amount, callback_url=game_callback_url,
                    good_name=good_name, passthrough=passthrough,
                    platform=platform, pay_channel=pay_channel
                )
        order.trade_id = uuid.uuid4().get_hex()
        order.status = 'S'
        order.save()
    else:
        order = orders[0]

    request_args = get_callback_arg_tuples(order)
    request_query_str = '&'.join(['='.join(item) for item in request_args])
    pay_callback_url = app.pay_callback_url
    parsed_u8_callback_url = urlparse.urlparse(pay_callback_url)
    new_u8_parsed_callback_url = urlparse.ParseResult(scheme=parsed_u8_callback_url.scheme, 
                                                   netloc=parsed_u8_callback_url.netloc,
                                                   path=parsed_u8_callback_url.path,
                                                   params=parsed_u8_callback_url.params,
                                                   query=request_query_str,
                                                   fragment=parsed_u8_callback_url.fragment)
    new_u8_callback_url = urlparse.urlunparse(new_u8_parsed_callback_url)
    callback_sign = get_signature(app.appsecret.encode('utf-8'), new_u8_callback_url)
    request_args.append(('Sign', callback_sign))
    args_map = dict(request_args)
    request_obj = urllib2.Request(pay_callback_url) # 创建请求对象
    request_obj.add_data(urllib.urlencode(args_map)) # 添加请求参数
    response = urllib2.urlopen(request_obj, timeout=settings.PAY_CALLBACK_TIMEOUT).read()
    print(response)

def start_budan(filename):
    f = open(filename)
    json_original = json.load(f)
    json_recorsds = json_original['RECORDS']
    for json_record in json_recorsds:
        print('processing:', json_record)
        appid = json_record['appID']
        app_order_id = json_record['orderID']
        amount = json_record['money']
        real_amount = amount
        good_name = json_record['productName']
        budan(appid, app_order_id, amount, real_amount, good_name)
        time.sleep(1)                

if __name__ == '__main__':
    pass