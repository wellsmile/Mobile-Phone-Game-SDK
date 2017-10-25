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

def login(appid, wechat_code, binduser):
    '''使用微信账户登陆本Heyi系统'''
    user = None
    apps = App.objects.filter(appid=appid)
    if not apps.exists():
        return user
    
    app = apps[0]
    thirdparty_app_infos = ThirdPartyAppInfo.objects.filter(app=app, thirdparty='wechat')
    if not thirdparty_app_infos.exists():
        return user
    
    thirdparty_app_info = thirdparty_app_infos[0]
    app_info_json = thirdparty_app_info.info
    if not app_info_json.strip():
        return user
    
    try:
        app_info_dict = json.loads(app_info_json)
        
        # 通过code获取refresh_token
        gettoken_wechat_response = requests.get(settings.WECHAT_GET_TOKEN_ENDPOINT+'access_token?appid={}&secret={}&code={}&grant_type=authorization_code'.format(app_info_dict['appid'], app_info_dict['appsecret'], wechat_code))
        gettoken_response_dict = json.loads(gettoken_wechat_response.content)
        refresh_token = gettoken_response_dict['refresh_token']
        
        # 通过refresh_token获取access_token
        refreshtoken_wechat_response = requests.get(settings.WECHAT_GET_TOKEN_ENDPOINT+'refresh_token?appid={}&grant_type=refresh_token&refresh_token={}'.format(app_info_dict['appid'], refresh_token))
        refreshtoken_response_dict = json.loads(refreshtoken_wechat_response.content)
        access_token = refreshtoken_response_dict['access_token']
        openid = refreshtoken_response_dict['openid']
        
        # 通过access_token和openid获取用户信息
        userinfo_wechat_response = requests.get(settings.WECHAT_USER_INFO_ENDPOINT+'?access_token={}&openid={}'.format(access_token, openid))
        userinfo_response_json = userinfo_wechat_response.content
        
        error_stack_logger.info('wechat oauth response: {}'.format(gettoken_wechat_response.content))
        wechat_userid = openid
        wechat_users = ThirdPartyUser.objects.filter(thirdparty='wechat', thirdparty_userid=wechat_userid)
        if wechat_users.exists():
            wechat_user = wechat_users[0]
            if binduser: # 有任何尝试绑定的行为，必须阻挡
                raise AlreadyBindThirdPartyError
        else:
            if binduser:
                wechat_user = ThirdPartyUser(user=binduser, thirdparty='wechat', thirdparty_userid=wechat_userid)
            else:
                username, password = onekey_username_password()
                user = User(username=username)
                user.set_password(password)
                user.id = uuid.uuid4().hex
                user.save()
                
                wechat_user = ThirdPartyUser(user=user, thirdparty='wechat', thirdparty_userid=wechat_userid)
            
        wechat_user.extra_info = userinfo_response_json
        wechat_user.save()
        
    except AlreadyBindThirdPartyError:
        raise 
    except Exception as e:
        error_stack_logger.fatal('LOGIN WITH WECHAT FAILED\t{}'.format(str(e)))
    else:
        return wechat_user.user