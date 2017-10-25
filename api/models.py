#coding=utf-8

from __future__ import unicode_literals

import time
import datetime
import random
import string
import hashlib

from utils.cache import user_cache

from django.conf import settings
from django.db import models

class PayType(models.Model):
    name = models.CharField(max_length=30, verbose_name=u'名字')
    identifier = models.CharField(max_length=20, verbose_name=u'标示符')
    seq = models.IntegerField(unique=True, verbose_name=u"优先级(小数字优先)")
    status = models.IntegerField(verbose_name=u"支付方式总开关 0-关 1-开")

    class Meta:
        verbose_name = u"Pay Type"
        verbose_name_plural = verbose_name
    
    def __unicode__(self):
        return self.name

class GamePayType(models.Model):
    game = models.ForeignKey('App', verbose_name=u'游戏')
    type = models.ForeignKey('PayType', verbose_name=u'支付方式')
    status = models.IntegerField(verbose_name=u'状态 0-关闭 1-开启')

    class Meta:
        verbose_name = u"Game Pay Type"
        verbose_name_plural = verbose_name
    
    def __unicode__(self):
        return '{}-{}'.format(self.game.name, self.type.identifier)
        
class App(models.Model):
    '''App definition'''
    appid = models.CharField(verbose_name="App ID", max_length=128, primary_key=True)
    name = models.CharField(verbose_name="App Name", max_length=128, db_index=True, default='')
    appkey = models.CharField(verbose_name="App Key", max_length=128, unique=True, db_index=True)
    appsecret = models.CharField(verbose_name="App Secret Key", max_length=128, default='')
    paykey = models.CharField(verbose_name="Pay key", max_length=128, default='')
    package_names = models.TextField(verbose_name="包名(bundle id)列表，用英文逗号隔开", blank=True, null=True)
    description = models.CharField(verbose_name="Short Description", max_length=512, default='')
    description_long = models.TextField(verbose_name="Long Description", default='')
    version_name = models.CharField(verbose_name="用于呈现给用户的版本", max_length=128, default='')
    app_size = models.BigIntegerField(verbose_name='Size of the app', default=0)
    latest_version_desc = models.CharField(verbose_name='更新描述', max_length=128)
    latest_version_code = models.IntegerField(verbose_name='version (int)', default=1)
    support_version_code_list = models.CharField(verbose_name='version support list', max_length=128)
    download_link = models.TextField(verbose_name='App download url', default='')
    pay_callback_url = models.URLField(verbose_name='支付回调地址', default='', max_length=256)
    pay_type = models.ManyToManyField(PayType, verbose_name='支持的支付方式')
    is_standalone = models.IntegerField(verbose_name='是否是单机应用', default=0)
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='create at', db_index=True)
    update_at = models.DateTimeField(auto_now=True, verbose_name='update at', db_index=True)
    
    def __unicode__(self):
        return self.name

class User(models.Model):
    '''user definition'''
    USER_STATE = ((0, '正常'), (1, '封号'))
    
    id = models.CharField(verbose_name="User ID", max_length=128, primary_key=True)
    phone = models.CharField(verbose_name="User Phone Number", max_length=128, blank=True, null=True, db_index=True)
    username = models.CharField(verbose_name="User Name", max_length=128, unique=True, null=True, db_index=True)
    imei = models.CharField(verbose_name="User imei", max_length=128, db_index=True, blank=True, null=True)
    password_hash = models.CharField(verbose_name="user password hash", max_length=128)
    password_salt = models.CharField(verbose_name="user password slat", max_length=128)
    guid = models.CharField(verbose_name='guid', db_index=True, max_length=128, null=True, blank=True)
    state = models.SmallIntegerField(verbose_name='用户状态', choices=USER_STATE, db_index=True, default=0)
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='create at', db_index=True)
    register_at = models.DateTimeField(verbose_name='register at', db_index=True, null=True, blank=True)
    auth_name = models.CharField(verbose_name="Auth_Name", max_length=128, default='')
    auth_idcard = models.CharField(verbose_name="Auth IDCard", max_length=128, default='')
    
    class Meta:
        unique_together = ('username', 'phone')
    
    def __unicode__(self):
        return self.username
    
    def __rand_slat__(self, length=6):
        myrg = random.SystemRandom()
        # If you want non-English characters, remove the [0:52]
        alphabet = string.letters[0:52] + string.digits
        pw = str().join(myrg.choice(alphabet) for _ in range(length))
        return pw
    
    @classmethod
    def generate_password(cls):
        """
        自动生成密码
        """
        password_list = random.sample(string.lowercase, 3) + random.sample(string.digits, 3)
        random.shuffle(password_list)
        return ''.join(password_list)

    def check_password(self, password):
        '''检查提供的明文密码是否与用户的密码相同'''
        return hashlib.md5(password+self.password_salt).hexdigest() == self.password_hash
    
    def set_password(self, password):
        '''自动设置用户的密码salt，并根据此密码salt和用户提供的明文密码，生成密码密文，check_password方法提供了检测机制来判断用户提供的密码是否正确'''
        password_salt = self.__rand_slat__()
        password = hashlib.md5(password + password_salt).hexdigest()
        self.password_salt = password_salt
        self.password_hash = password

    def set_md5_password(self, password):
        '''设置密码密文'''
        pwd = hashlib.md5(password).hexdigest()
        self.md5_password = pwd

    @classmethod
    def get_uid_by_session(cls, sessionid):
        '''从缓存中获取对应的session ID'''
        return user_cache.get(str(sessionid))

    @classmethod
    def set_sessionid(cls, uid, sessionid,expire=30):
        '''缓存sessionID与UID的映射关系'''
        user_cache.set(str(sessionid), uid, expire)
    
    @classmethod
    def del_sessionid(cls, sessionid):
        '''删除sessionid'''
        user_cache.delete(sessionid)

    @classmethod
    def generate_sessionid(cls, uid, appkey):
        '''根据uid，appkey和当前时间生成一个session ID'''
        data = str(uid) + appkey + str(time.time())
        sessionid = hashlib.md5(data).hexdigest()
        return sessionid

    @classmethod
    def generate_verifycode(cls):
        """生成验证码"""
        return ''.join(random.sample(string.digits, settings.VERIFY_CODE_LENGTH))

    @classmethod
    def save_verifycode(cls, code, phone, expire=30*60):
        """保存验证码"""
        user_cache.set(phone, code, expire)

    @classmethod
    def get_verifycode(cls, phone):
        """获取验证码"""
        return user_cache.get(str(phone))

    @classmethod
    def del_verifycode(cls, phone):
        """清空验证码"""
        return user_cache.delete(str(phone))
    
    @classmethod
    def generate_login_verifycode(cls):
        """生成登陆验证码"""
        return ''.join(random.sample(string.digits, settings.VERIFY_CODE_LENGTH))

    @classmethod
    def save_login_verifycode(cls, code, phone, expire=30*60):
        """保存登陆验证码"""
        key = "login-verify:"+str(phone)
        user_cache.set(key, str(code), expire)

    @classmethod
    def get_login_verifycode(cls, phone):
        """获取登陆验证码"""
        key = "login-verify:"+str(phone)
        return user_cache.get(key)

    @classmethod
    def del_login_verifycode(cls, phone):
        """清空登录验证码"""
        key = "login-verify:"+str(phone)
        return user_cache.delete(key)

class UserGameOrder(models.Model):

    ORDER_STATUS = [
        ('I', u'待付款'),
        ('S', u'交易成功'),
        ('F', u'交易失败'),
        ('R', u'退款'),
        ('C', u'交易关闭'),
        ('SS', u'iTunes Sandbox交易成功'),
        ('E', u'iTunes （线上环境）交易异常'),
    ]

    NOTICE_STATUS = [
        (0, u'未通知'),
        (1, u'成功'),
        (2, u'失败'),
    ]

    PLATFORM = [
        (1, u'TV'),
        (2, u'手游'),
    ]

    ORDER_SOURCE = [
        (1, u'支付'),
        (2, u'充值并支付'),
    ]

    #foreign key
    user = models.ForeignKey(User)
    app = models.ForeignKey(App)

    amount = models.IntegerField(verbose_name=u'支付金额，单位(分)')
    real_amount = models.IntegerField(verbose_name=u'真实支付金额，单位(分)', default=0)
    currency = models.CharField(verbose_name=u'订单对应的货币单位', max_length=16, default='cny')
    #id
    trade_id = models.CharField(verbose_name=u"支付中心订单id", max_length=32, db_index=True, unique=True, null=True)
    game_order_id = models.CharField(verbose_name=u"游戏商订单id", max_length=64, unique=True, db_index=True)

    #time
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u"创建时间", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name=u"最后更新时间")
    int_date = models.IntegerField(verbose_name=u'整形日期 20150102', db_index=True)

    #others
    callback_url = models.CharField(max_length=256, verbose_name=u"回调地址")
    pay_channel = models.CharField(max_length=20, verbose_name=u"支付通道（100:支付宝；99:苹果支付；98:银联支付；96:谷歌支付）", default='',db_index=True)

    good_name = models.CharField(verbose_name=u"商品名称", max_length=20, default='游戏道具')
    passthrough = models.CharField(verbose_name=u'透传参数', max_length=128, default='')
    sign = models.CharField(verbose_name=u'数字签名', max_length=256,default='')
    platform = models.IntegerField(verbose_name=u'游戏平台', choices=PLATFORM, default=1, db_index=True)

    #status
    notice_status = models.IntegerField(verbose_name=u'通知cp状态', choices=NOTICE_STATUS, db_index=True)
    order_status = models.CharField(max_length=2, verbose_name=u"订单状态", choices=ORDER_STATUS, db_index=True)

    #notice desc
    notice_desc = models.CharField(verbose_name=u'通知游戏服务商失败原因', max_length=256, default='')

    order_source = models.IntegerField(verbose_name=u'订单来源', default=1, choices=ORDER_SOURCE)
    
    productid = models.CharField(verbose_name=u'通知U8发货时所需的productid', max_length=128, default='')

    objects = models.Manager()
    
    def __unicode__(self):
        return self.trade_id
    
    class Meta:
        verbose_name = u"User Order"
        verbose_name_plural = verbose_name
    
    @classmethod
    def create_order(cls, user, app, amount, **kwargs):

        order = UserGameOrder()
        order.user = user
        order.app = app
        order.order_status = 'I'
        order.amount = amount
        order.notice_status = 0
        #int_date做查询用
        order.int_date = int(datetime.datetime.now().strftime('%Y%m%d'))
        #other
        #order.sign = kwargs.get('sign')
        order.game_order_id = kwargs.get('game_order_id')
        order.callback_url = kwargs.get('callback_url', '')
        order.passthrough = kwargs.get('passthrough', '')
        order.good_name = kwargs.get('good_name')
        order.platform = kwargs.get('platform')
        order.order_source = kwargs.get('order_source', 1)
        pay_channel = kwargs.get('pay_channel')
        order.pay_channel = pay_channel
        order.real_amount = kwargs.get('real_amount', 0)
        order.currency = kwargs.get('currency', '')
        order.productid = kwargs.get('productid', '')
        order.save()

        return order

    @classmethod
    def update_order_by_trade(cls, trade_id, **kwargs):
        order = UserGameOrder.objects.get(
            trade_id=trade_id
        )
        return order

    @classmethod
    def update_order_by_game_order_id(cls, game_order_id, **kwargs):
        order = UserGameOrder.objects.get(
            game_order_id=game_order_id
        )
        return order

class ThirdPartyUser(models.Model):
    user = models.ForeignKey(User)
    thirdparty = models.CharField(max_length=32, db_index=True)
    thirdparty_userid = models.CharField(max_length=128, unique=True)
    extra_info = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    def __unicode__(self):
        return self.thirdparty_userid

class ThirdPartyAppInfo(models.Model):
    '''海外app通过审核后的一些app身份标识信息存储'''
    THIRDPARTY_CHOICES = (('facebook', 'facebook'), 
                       ('google', 'google'),
                       ('qq', 'qq'),
                       ('wechat', 'wechat'),
                       ('weibo', 'weibo'))
    app = models.ForeignKey(App)
    thirdparty = models.CharField(max_length=64, choices=THIRDPARTY_CHOICES)
    info = models.TextField(verbose_name='in JSON format', blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('app', 'thirdparty')
    
    def __unicode__(self):
        return self.app.name    

class AppPayInfo(models.Model):
    '''存储各个app的各个付款方式所需的参数'''
    PAYTYPE_CHOICES = (('wechatpay', 'wechatpay'), 
                       ('alipay', 'alipay'),
                       ('tencentpay', 'tencentpay'),
                       ('googlepay', 'googlepay'),
                       ('unionpay', 'unionpay'),
                       ('iap', 'iap'),
                       ('iapppay','iapppay'),
                       ('molpay','molpay'))
    app = models.ForeignKey(App)
    paytype = models.CharField(max_length=64, choices=PAYTYPE_CHOICES)
    info = models.TextField(verbose_name='in JSON format', blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('app', 'paytype')
    
    def __unicode__(self):
        return self.app.name 
        
class IAPReceiptHistory2(models.Model):
    '''只作为一个历史缓存记录'''
    STATE = [
        (0, '未验证'),
        (1, '验证成功'),
        (2, '验证失败'),
    ]
    iap_digest = models.CharField(verbose_name='苹果支付验证串的md5值', max_length=255, unique=True)
    trade_id = models.CharField(verbose_name=u"支付中心订单id", max_length=32, db_index=True, blank=True, null=True)
    state = models.SmallIntegerField(verbose_name='记录当前订单是否已经', choices=STATE, default=0)
    bundle_id = models.CharField(verbose_name='iOS bundle_id', max_length=128, blank=True, null=True)
    quantity = models.IntegerField(verbose_name='iTunes IAP quantity', blank=True, null=True)
    product_id = models.CharField(verbose_name='iTunes IAP product_id', max_length=255, blank=True, null=True)
    transaction_id = models.CharField(verbose_name='iTunes IAP transaction_id', max_length=255, blank=True, null=True, db_index=True)
    purchase_date_ms = models.BigIntegerField(verbose_name='iTunes IAP purchase_date_ms', blank=True, null=True)
    original_transaction_id = models.CharField(verbose_name='iTunes IAP original_transaction_id', max_length=255, blank=True, null=True, db_index=True)
    original_purchase_date_ms = models.BigIntegerField(verbose_name='iTunes IAP original_purchase_date_ms', blank=True, null=True)
    is_sandbox = models.BooleanField(verbose_name='是否是沙箱环境', default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return self.iap_digest
    