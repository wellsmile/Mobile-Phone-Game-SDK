#coding=utf-8

from django.conf import settings

from api.tasks import track
from utils.usercenter.access import get_request_ip

def apitrack(event_name, context=None, meta=None):
    '''API track接口'''
    if settings.MATRIX_SWITCH:
        track.apply_async(args=[event_name, context, meta])

def get_request_context(request):
    '''从请求对象中获取上下文信息，用于日志记录'''
    INTERESTED_HTTP_PARAMS = [
            'CONTENT_LENGTH',
            'CONTENT_TYPE',
            'HTTP_HOST',
            'HTTP_REFERER',
            'HTTP_USER_AGENT',
            'REMOTE_ADDR',
            'REMOTE_HOST',
            'REQUEST_METHOD',
            'SERVER_NAME',
            'SERVER_PORT',
        ]
    http_context = {item.lower(): request.META.get(item, '') for item in INTERESTED_HTTP_PARAMS}
    get_params = request.GET.dict()
    post_params = request.POST.dict()
    
    if get_params.has_key('raw_data'):
        get_params.pop('raw_data')
    if post_params.has_key('raw_data'):
        post_params.pop('raw_data')
    
    context = {
                'path': request.path,
                'get_params': get_params,
                'post_params': post_params,
            }

    meta = {
        'ip': get_request_ip(request)
    }
    context.update(http_context)
    return context, meta