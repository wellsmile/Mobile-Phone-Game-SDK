#coding=utf-8
'''
Created on Oct 22, 2016

@author: Felix
'''
from facebook.facebook import login as facebook_login
from google.google import login as google_login
from qq.qq import login as qq_login
from wechat.wechat import login as wechat_login
from weibo.weibo import login as weibo_login
from api.models import ThirdPartyUser

import logging
error_stack_logger = logging.getLogger('error_stack')

class ThirdPartyLogin(object):
    def __init__(self, appid, thirdparty='facebook', credential=None, binduser=None):
        self._appid = appid
        self._thirdparty = thirdparty
        self._credential = credential
        self._binduser = binduser
    
    def user(self):
        thirdparty_user = None
        if self._thirdparty == 'facebook':
            thirdparty_user = facebook_login(self._appid, self._credential, self._binduser)
        elif self._thirdparty == 'google':
            thirdparty_user = google_login(self._appid, self._credential, self._binduser)
        elif self._thirdparty == 'wechat':
            thirdparty_user = wechat_login(self._appid, self._credential, self._binduser)
        elif self._thirdparty == 'qq':
            thirdparty_user = qq_login(self._appid, self._credential, self._binduser)
        elif self._thirdparty == 'ali':
            thirdparty_user = None
        elif self._thirdparty == 'weibo':
            thirdparty_user = weibo_login(self._appid, self._credential, self._binduser)
        return thirdparty_user

    @classmethod
    def bind_state(cls, user):
        thirdparty_users = ThirdPartyUser.objects.filter(user=user)
        if thirdparty_users.exists():
            return thirdparty_users[0].thirdparty