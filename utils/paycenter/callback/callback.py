#coding=utf-8
'''
Created on Sep 10, 2016

@author: Felix
@summary: 用户付费确认之后需要向
'''

from django.conf import settings

def get_callback_arg_tuples(order, others=[]):
    '''
    @param order: 本地订单的一条记录，从这个订单记录中获取相关的数据之后，
    按照settings.PAY_CALLBACK_LOCAL_REMOTE_MAPPING设置的顺序提取成[(k1, v1), (k2, v2)...]的形式，
    由于验签的内容依赖于这个顺序，所以要在配置中固定好顺序
    @param others: 一个列表，类似于：[('ProductID', '')] 
    '''
    base_args = [(item[0], str(getattr(order, item[1]))) for item in settings.PAY_CALLBACK_LOCAL_REMOTE_MAPPING]
    base_args.extend(others)
    return base_args