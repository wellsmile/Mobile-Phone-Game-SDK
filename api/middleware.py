#coding=utf-8
'''
Created on Nov 1, 2016

@author: Felix
'''
import hashlib

from django.conf import settings
from django.http import JsonResponse

from api.models import App
from utils.cache import appid_appsecret_cache
from utils.logcenter import apitrack
from utils.logcenter import get_request_context

class StatsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path in settings.API_DEFINATIONS or request.path in settings.U8_RELATED_APIS:
            event_name = 'request received'
            context, meta = get_request_context(request)
            apitrack(event_name, context, meta)
        
        response = self.get_response(request)
        return response

class ValidateMiddleware(object):
    '''API规格验证、请求签名合法性验证'''
    def __init__(self, get_response):
        self.get_response = get_response
        self._appsecret2 = '***********************************'
    
    def __call__(self, request):
        if request.path in settings.API_DEFINATIONS:
            api_defination = settings.API_DEFINATIONS[request.path]
            method_name = api_defination['method']
            required_params = api_defination['required_params']
            
            raw_parameters = getattr(request, method_name)
            parameter_dict = raw_parameters.dict()
            # 用于日志记录，记录非法的API请求
            event_name = 'invalid request'
            context, meta = get_request_context(request)
            # 用于日志记录 END

            for parameter_name in required_params:
                parameter_value = raw_parameters.get(parameter_name, None)
                if (parameter_value is None) or (not parameter_value.strip()):
                    # 记录日志
                    context['reason'] = 'missing parameter %s' % parameter_name
                    apitrack(event_name, context, meta)
                    # 记录日志 END
                    return JsonResponse({'status': 'failed', 'code': -1, 'desc': '%s missing' % parameter_name})
        
            sign = parameter_dict.pop('sign') if 'sign' in parameter_dict else None # 消除掉sign，剩下待签名的参数
            appid = parameter_dict.get('appid', None)
            sdk_api_ver = parameter_dict.get('sdk_api_ver', None)
            valid = False
            if sign and appid:
                cached_appsecret = appid_appsecret_cache.get(appid)
                try:
                    appsecret = cached_appsecret if cached_appsecret else App.objects.get(appid=appid).appsecret
                except App.DoesNotExist:
                    context['reason'] = 'app not exists'
                    apitrack(event_name, context, meta)
                else:
                    cached_appsecret or appid_appsecret_cache.set(appid, appsecret)
                    parameter_str = '******'.join(['******'.join(item) for item in sorted(parameter_dict.items(), key=lambda x: x[0], reverse=False)])
                    to_be_signed_str = '******'.join([parameter_str, appsecret])
                    server_sign = hashlib.md5(to_be_signed_str).hexdigest()
                    
                    if sdk_api_ver == '1.0.1':
                        to_be_signed_str = '%s%s' % (self._appsecret2, server_sign)
                        server_sign = hashlib.md5(to_be_signed_str).hexdigest()
                    
                    if sign == server_sign:
                        valid = True
                    else:
                        context['reason'] = 'invalid sign'
                        context['server_signed_str'] = to_be_signed_str
                        context['server_sign'] = server_sign
                        context['sign'] = sign
                        apitrack(event_name, context, meta)
            else:
                context['reason'] = 'sign or appid missing'
                apitrack(event_name, context, meta)       
            
            if not valid:
                return JsonResponse({'status': 'failed', 'code': -999, 'desc': 'invalid request' })
            
        response = self.get_response(request)
        return response