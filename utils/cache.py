#coding=utf-8
'''
Created on Aug 26, 2016

@author: Felix
'''
import redis
from django.conf import settings

user_cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=2)
verifycode_expired_info_cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=1)
appid_appsecret_cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=3)
user_ispay_cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=4)

def set_user_ispay_cache(appid, userid, amount=0):
    '''设置用户在某一游戏内的付费标记，用于个性化登陆体验：比如弹出绑定手机提示'''
    key = '%s_%s' % (appid, userid)
    current_value = user_ispay_cache.get(key)
    try:
        count, amount = map(int, current_value.split('_'))
    except:
        count, amount = 0, 0
    count += 1
    amount += int(amount) # cent unit
    value = '%s_%s' % (count, amount)
    user_ispay_cache.set(key, value)

def get_user_ispay_cache(appid, userid):
    '''获取用户是否付费的相关信息'''
    key = '%s_%s' % (appid, userid)
    return user_ispay_cache.get(key)
    
if __name__ == '__main__':
    r = redis.StrictRedis(host='192.168.99.100', port=6379)
    print(r.get('a'))    