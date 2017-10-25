#coding=utf-8
'''
Created on Oct 13, 2016
@summary: 获取一些用户请求相关的信息，用于了解用户请求的基本状况

@author: Felix
'''

def get_request_ip(request):
    '''获取用户请求的IP地址'''
    remote_ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if remote_ip:
        remote_ip = remote_ip.split(',')[0]
    else:
        remote_ip = request.META.get('REMOTE_ADDR', '')
    return remote_ip