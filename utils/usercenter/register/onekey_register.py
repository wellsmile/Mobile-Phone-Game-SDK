#coding=utf-8
'''
Created on Oct 10, 2016

@author: Felix
'''
import random

from django.conf import settings

from api.models import User

def onekey_username_password():
    '''为一键注册用户生成随机的用户名和密码'''
    
    # 一键注册功能需要服务器生成用户名和密码，并保证用户名的唯一性
    while True:
        onekey_username = ''.join(random.sample(settings.ALPHA_DIGIT_SET, 7))
        user_exists = User.objects.filter(username=onekey_username).exists()
        if not user_exists:
            break
    
    onekey_password = ''.join(random.sample(settings.DIGIT_SET, 6))
    return onekey_username, onekey_password