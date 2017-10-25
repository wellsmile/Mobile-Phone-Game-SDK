#coding=utf-8
'''
Created on Oct 22, 2016

@author: Felix
'''
import uuid
import urllib
import urllib2
import json
import logging

from django.conf import settings

from api.models import ThirdPartyUser, User, App, ThirdPartyAppInfo
from utils.usercenter.register.onekey_register import onekey_username_password
from utils.usercenter.login.exceptions import AlreadyBindThirdPartyError

error_stack_logger = logging.getLogger('error_stack')

def login(appid, gg_tokenstring, binduser):
    '''使用谷歌账户登陆本Heyi系统'''
    user = None
    apps = App.objects.filter(appid=appid)
    if not apps.exists():
        return user
    
    app = apps[0]
    thirdparty_app_infos = ThirdPartyAppInfo.objects.filter(app=app, thirdparty='google')
    if not thirdparty_app_infos.exists():
        return user
    
    thirdparty_app_info = thirdparty_app_infos[0]
    app_info_json = thirdparty_app_info.info
    if not app_info_json.strip():
        return user
    
    try:
        app_info_list = json.loads(app_info_json)
        for app_info_dict in app_info_list:
            if app_info_dict.has_key('redirect_appid'):
                redirect_client = ThirdPartyAppInfo.objects.get(app__appid=app_info_dict['redirect_appid'], thirdparty='google')
                app_info_list.extend(json.loads(redirect_client.info))
        google_client_ids = [item['client_id'] for item in app_info_list]
        
        data = {
            'id_token': gg_tokenstring,
        }
        url_values = urllib.urlencode(data)
        full_url = settings.GOOGLE_TOKEN_INFO_ENDPOINT + '?' + url_values
        response_json = urllib2.urlopen(full_url).read()
        response_dict = json.loads(response_json)
        error_stack_logger.info('Google oauth response: {}'.format(response_json))
        if response_dict['aud'] in google_client_ids and \
        response_dict['iss'] in ['accounts.google.com', 'https://accounts.google.com']:
            gg_userid = response_dict['sub']
            gg_users = ThirdPartyUser.objects.filter(thirdparty='google', thirdparty_userid=gg_userid)
            if gg_users.exists():
                gg_user = gg_users[0]
                if binduser: # 有任何尝试绑定的行为，必须阻挡
                    raise AlreadyBindThirdPartyError
            else:
                if binduser:
                    gg_user = ThirdPartyUser(user=binduser, thirdparty='google', thirdparty_userid=gg_userid)
                else:
                    username, password = onekey_username_password()
                    user = User(username=username)
                    user.set_password(password)
                    user.id = uuid.uuid4().hex
                    user.save()
                    
                    gg_user = ThirdPartyUser(user=user, thirdparty='google', thirdparty_userid=gg_userid)
                
            gg_user.extra_info = response_json
            gg_user.save()
        else:
            error_stack_logger.fatal('LOGIN WITH GOOGLE FAILED RESPONSE CHECK FAILED')
            return user
    except AlreadyBindThirdPartyError:
        raise 
    except Exception as e:
        error_stack_logger.fatal('LOGIN WITH GOOGLE FAILED\t{}'.format(str(e)))
    else:
        return gg_user.user