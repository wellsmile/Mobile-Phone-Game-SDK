#coding=utf-8
'''
Created on Aug 26, 2016

@author: Felix
'''
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='Heyi Index'),
    url(r'^game/initial$', views.initial, name='user_information'),
    url(r'^game/nick/register$', views.nick_register, name='user_register'),
    url(r'^game/nick/repassword$', views.repassword, name='repassword'),
    url(r'^game/bindphone/request_verifycode$', views.request_verifycode, name='request_verifycode'),
    url(r'^game/bindphone/bindphone$', views.bindphone, name='bindphone'),
    url(r'^game/bindthirdparty$', views.bindthirdparty, name='bindthirdparty'),
    url(r'^game/login$', views.login, name='login'),
    url(r'^game/logout$', views.logout, name='logout'),
    url(r'^game/verify_receipt$', views.verify_receipt, name='verify_receipt'),
    url(r'^game/user/information$', views.user_information, name='user_information'),
    url(r'^game/check_apporderid$', views.check_apporderid, name='check_apporderid'),
    url(r'^game/do_pay$', views.do_pay, name='do_pay'),
    url(r'^game/verify_alipay$', views.verify_alipay, name='verify_alipay'),
    url(r'^game/verify_unionpay$', views.verify_unionpay, name='verify_uionpay'),
    url(r'^game/unionpay_front$', views.unionpay_front, name='unionpay_front'),
    url(r'^game/touristlogin$', views.touristlogin, name='touristlogin'),
    url(r'^game/authenticate$', views.real_name_authentication, name='real_name_authentication'),
    
    #谷歌支付相关
    url(r'^game/verify_googlepay$', views.verify_googlepay, name='verify_googlepay'),
    # 微信支付相关
    url(r'^game/verify_wechatpay$', views.verify_wechatpay, name='verify_wechatpay'),
    # 爱贝支付相关
    url(r'^game/verify_iapppay$', views.verify_iapppay, name='verify_iapppay'),
    # MOL支付相关
    url(r'^game/verify_molpay$', views.verify_molpay, name='verify_molpay'),
    # 分期乐支付相关
    url(r'^game/verify_fenqilepay$', views.verify_fenqilepay, name='verify_fenqilepay'),
    # 腾讯支付相关
#     url(r'^game/verify_tencentpay$', views.verify_tencentpay, name='verify_tencentpay'),
    
    url(r'^game/resetpassword/request_verifycode_resetpassword$', views.request_verifycode_resetpassword, name='request_verifycode_resetpassword'),
    url(r'^game/resetpassword/resetpassword$', views.resetpassword, name='resetpassword'),
    url(r'^game/user/profile$', views.user_profile, name='user_phone')
]