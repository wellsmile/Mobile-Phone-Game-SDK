#coding=utf-8
'''
Created on 2016年12月1日

@author: xiaochengcao
'''
import uuid
import json
import logging

import requests

from django.conf import settings

from api.models import ThirdPartyUser, User, App, ThirdPartyAppInfo
from utils.usercenter.register.onekey_register import onekey_username_password
from utils.usercenter.login.exceptions import AlreadyBindThirdPartyError

error_stack_logger = logging.getLogger('error_stack')

def login(appid, weibo_tokenstring, binduser):
    '''使用qq账户登陆本Heyi系统'''
    user = None
    apps = App.objects.filter(appid=appid)
    if not apps.exists():
        return user
    
    app = apps[0]
    thirdparty_app_infos = ThirdPartyAppInfo.objects.filter(app=app, thirdparty='weibo')
    if not thirdparty_app_infos.exists():
        return user
    
    thirdparty_app_info = thirdparty_app_infos[0]
    app_info_json = thirdparty_app_info.info
    if not app_info_json.strip():
        return user
    
    try:
        app_info_dict = json.loads(app_info_json)
        weibo_respon = requests.post(settings.WEIBO_TOKEN_INFO_ENDPOINT,{'access_token':weibo_tokenstring})
        response_dict = json.loads(weibo_respon.content)
        error_stack_logger.info('weibo oauth response: {}'.format(weibo_respon.content))
        if response_dict['appkey'] == app_info_dict['appkey']:
            weibo_userid = response_dict['uid']
            weibo_users = ThirdPartyUser.objects.filter(thirdparty='weibo', thirdparty_userid=weibo_userid)
            if weibo_users.exists():
                weibo_user = weibo_users[0]
                if binduser: # 有任何尝试绑定的行为，必须阻挡
                    raise AlreadyBindThirdPartyError
            else:
                if binduser:
                    weibo_user = ThirdPartyUser(user=binduser, thirdparty='weibo', thirdparty_userid=weibo_userid)
                else:
                    username, password = onekey_username_password()
                    user = User(username=username)
                    user.set_password(password)
                    user.id = uuid.uuid4().hex
                    user.save()
                    
                    weibo_user = ThirdPartyUser(user=user, thirdparty='weibo', thirdparty_userid=weibo_userid)
                
            weibo_user.extra_info = json.dumps(response_dict)
            weibo_user.save()
        else:
            error_stack_logger.fatal('LOGIN WITH WEIBO FAILED RESPONSE CHECK FAILED')
            return user
    except AlreadyBindThirdPartyError:
        raise 
    except Exception as e:
        error_stack_logger.fatal('LOGIN WITH WEIBO FAILED\t{}'.format(str(e)))
    else:
        return weibo_user.user