#coding=utf-8
'''
Created on Oct 18, 2016

@author: Felix
'''
import uuid
import logging
import json
import urllib
import urllib2
import hmac
import hashlib

from django.conf import settings

from api.models import ThirdPartyUser, User, App, ThirdPartyAppInfo

from utils.usercenter.register.onekey_register import onekey_username_password
from utils.usercenter.login.exceptions import AlreadyBindThirdPartyError

error_stack_logger = logging.getLogger('error_stack')

def login(appid, fb_tokenstring, binduser):
    user = None
    
    apps = App.objects.filter(appid=appid)
    if not apps.exists():
        error_stack_logger.fatal('THIRDPARTY APP EMPTY')
        return user
    
    app = apps[0]
    thirdparty_app_infos = ThirdPartyAppInfo.objects.filter(app=app, thirdparty='facebook')
    if not thirdparty_app_infos.exists():
        error_stack_logger.fatal('THIRDPARTY APP INFO EMPTY')
        return user
    
    thirdparty_app_info = thirdparty_app_infos[0]
    app_info_json = thirdparty_app_info.info
    if not app_info_json.strip():
        error_stack_logger.fatal('THIRDPARTY INFO JSON EMPTY')
        return user
    
    try:
        app_info_dict = json.loads(app_info_json)
        appsecret_proof = hmac.new(app_info_dict['appsecret'].encode('utf-8'), fb_tokenstring, digestmod=hashlib.sha256).hexdigest()
        error_stack_logger.info('THIRDPARTY APP INFO: {}'.format(app_info_json))
        data = {
            'access_token': fb_tokenstring,
            'appsecret_proof': appsecret_proof,
            'fields': 'name,id',
        }
        url_values = urllib.urlencode(data)
        full_url = settings.FB_GRAPH_API_ENDPOINT + 'me/?' + url_values        
        
        response_json = urllib2.urlopen(full_url).read()
        error_stack_logger.info('Facebook Oauth response: {}'.format(response_json))
        response_dict = json.loads(response_json)
        fb_userid = response_dict['id']
        
        fb_users = ThirdPartyUser.objects.filter(thirdparty='facebook', thirdparty_userid=fb_userid)
        if fb_users.exists():
            fb_user = fb_users[0]
            if binduser: # 有任何尝试绑定的行为，必须阻挡
                raise AlreadyBindThirdPartyError
        else:
            if binduser: # 直接绑定此用户
                fb_user = ThirdPartyUser(user=binduser, thirdparty='facebook', thirdparty_userid=fb_userid)
            else:
                username, password = onekey_username_password()
                user = User(username=username)
                user.set_password(password)
                user.id = uuid.uuid4().hex
                user.save()
                
                fb_user = ThirdPartyUser(user=user, thirdparty='facebook', thirdparty_userid=fb_userid)
        
        fb_user.extra_info = response_json
        fb_user.save()
    except AlreadyBindThirdPartyError:
        raise
    except Exception as e:
        error_stack_logger.fatal('LOGIN WITH FACEBOOK FAILED\t{}'.format(str(e)))
    else:
        return fb_user.user
