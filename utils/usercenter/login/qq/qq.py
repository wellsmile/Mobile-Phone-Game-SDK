#coding=utf-8
'''
Created on 2016年12月1日

@author: xiaochengcao
'''
import uuid
import json
import logging

from django.conf import settings

import requests

from api.models import ThirdPartyUser, User, App, ThirdPartyAppInfo
from utils.usercenter.register.onekey_register import onekey_username_password
from utils.usercenter.login.exceptions import AlreadyBindThirdPartyError

error_stack_logger = logging.getLogger('error_stack')

def login(appid, qq_tokenstring, binduser):
    '''使用qq账户登陆本Heyi系统'''
    user = None
    apps = App.objects.filter(appid=appid)
    if not apps.exists():
        return user
    
    app = apps[0]
    thirdparty_app_infos = ThirdPartyAppInfo.objects.filter(app=app, thirdparty='qq')
    if not thirdparty_app_infos.exists():
        return user
    
    thirdparty_app_info = thirdparty_app_infos[0]
    app_info_json = thirdparty_app_info.info
    if not app_info_json.strip():
        return user
    
    try:
        app_info_dict = json.loads(app_info_json)
        qq_respon = requests.get(settings.QQ_TOKEN_INFO_ENDPOINT,{'access_token':qq_tokenstring})
        response_dict = json.loads(qq_respon.content.split(' ')[1])
        error_stack_logger.info('qq oauth response: {}'.format(qq_respon.content))
        if response_dict['client_id'] == app_info_dict['client_id']:
            qq_userid = response_dict['openid']
            qq_users = ThirdPartyUser.objects.filter(thirdparty='qq', thirdparty_userid=qq_userid)
            if qq_users.exists():
                qq_user = qq_users[0]
                if binduser: # 有任何尝试绑定的行为，必须阻挡
                    raise AlreadyBindThirdPartyError
            else:
                if binduser:
                    qq_user = ThirdPartyUser(user=binduser, thirdparty='qq', thirdparty_userid=qq_userid)
                else:
                    username, password = onekey_username_password()
                    user = User(username=username)
                    user.set_password(password)
                    user.id = uuid.uuid4().hex
                    user.save()
                    
                    qq_user = ThirdPartyUser(user=user, thirdparty='qq', thirdparty_userid=qq_userid)
                
            qq_user.extra_info = json.dumps(response_dict)
            qq_user.save()
        else:
            error_stack_logger.fatal('LOGIN WITH QQ FAILED RESPONSE CHECK FAILED')
            return user
    except AlreadyBindThirdPartyError:
        raise 
    except Exception as e:
        error_stack_logger.fatal('LOGIN WITH QQ FAILED\t{}'.format(str(e)))
    else:
        return qq_user.user