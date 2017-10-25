#coding=utf-8
'''
Created on Aug 30, 2016

@author: Felix
'''
from __future__ import absolute_import

import hashlib
import json
import logging
import uuid
import urlparse
import urllib
import urllib2

import itunesiap
import itunesiap.exceptions
from celery import shared_task
from celery import Task

from django.conf import settings
from .models import User, App, UserGameOrder, ThirdPartyAppInfo, IAPReceiptHistory2
from utils.signature import get_signature
from utils.paycenter.callback.callback import get_callback_arg_tuples
from utils.cache import set_user_ispay_cache

from utils.paycenter.googlepay.googlepay import token_refresh as googlepay_token_refresh
from utils.paycenter.googlepay.googlepay import check_product_status as googlepay_product_status

error_stack_logger = logging.getLogger('error_stack')
ios_receipt_logger = logging.getLogger('ios_receipt')

class LogTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        '''任务最终失败时，记录日志'''
        error_stack_logger.fatal('CELERY: IAP VERIFYING CALLBACK U8 FAIL DETECTED IN ON_FAILURE\t{}\t{}\t{}\t{}\t{}'.format('\t'.join('%s' % tostrtmp for tostrtmp in args), str(exc), task_id, einfo.traceback, self.request.retries))
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        '''任务重试时，记录日志'''
        error_stack_logger.warning('CELERY: IAP VERIFYING RETRING CALLBACK U8 DETECTED IN ON_RETRY\t{}\t{}\t{}\t{}\t{}'.format('\t'.join('%s' % tostrtmp for tostrtmp in args), str(exc), task_id, einfo.traceback, self.request.retries))
    
class U8ResponseException(Exception):
    pass

@shared_task(bind=True, base=LogTask)
def iap_verify_receipt(self, verify_from, appid, amount, app_order_id, good_name, pay_channel, userid, **kwargs):
    '''使用rawdata作为凭证请求苹果的服务器，获取支付回执信息'''
    args_string = '\t'.join([verify_from, appid, amount, app_order_id, good_name, pay_channel, userid]) # for logging
    raw_data = kwargs.get('raw_data')
    
    raw_data_digest = hashlib.sha1(raw_data).hexdigest() # 用于判断是否重复使用了一个支付凭证，如果重复直接拒绝
    iap_receipt_history, created = IAPReceiptHistory2.objects.get_or_create(iap_digest=raw_data_digest)
    
    # 本处理逻辑中涉及到的重要事件
    IAP_VERIFY_ERROR = settings.API_IMPORTANT_EVENTS.IAP_VERIFY_ERROR
    IAP_VERIFY_INFO = settings.API_IMPORTANT_EVENTS.IAP_VERIFY_INFO
    REUQEST_U8 = settings.API_IMPORTANT_EVENTS.REUQEST_U8
    raw_args = {
        'appid': appid,
        'amount': amount,
        'app_order_id': app_order_id,
        'good_name': good_name,
        'pay_channel': pay_channel,
        'userid': userid,
    }
    context = {}
    context['args_map'] = raw_args
    context['pay_channel'] = pay_channel
    
    if (not created) and (iap_receipt_history.state == 1):
        context['reason'] = 'duplicated receipt'
        _track(IAP_VERIFY_ERROR, context)
        return
    
    if verify_from != '1':
        context['reason'] = 'verify_from should be 1'
        _track(IAP_VERIFY_ERROR, context)
        return
    
    try:
        IS_SANDBOX = True
        response = None
        try:
            with itunesiap.env.review:
                response = itunesiap.verify(raw_data)
        except itunesiap.exceptions.InvalidReceipt as e:
            context['reason'] = 'exception when request iap endpoint %s' % str(e)
            _track(IAP_VERIFY_ERROR, context)
        
        if not response:
            context['reason'] = 'response from iap is none'
            _track(IAP_VERIFY_ERROR, context)
            return
        
        if response.status == 0:
            IS_SANDBOX = response['environment'].lower() == 'sandbox'
            NEED_NOTIFY = True
            
            try:
                app = App.objects.get(appid=appid)
            except App.DoesNotExist:
                context['reason'] = 'app not exists %s' % appid
                _track(IAP_VERIFY_ERROR, context)
                return
            
            ###### 校验包名
            try:
                response.receipt.in_app.sort(key=lambda x: int(getattr(x, 'original_purchase_date_ms')))
                last_in_app = response.receipt.last_in_app
                ios_receipt_logger.info('{}\t{}\t{}\t{}'.format(raw_data_digest, raw_data, args_string, response)) # 记录支付凭证摘要何其原始值的对应关系到日志
                # 通过original_transaction_id防止重复发货
                try:
                    _original_transaction_id = getattr(last_in_app, 'original_transaction_id')
                except:
                    _original_transaction_id = None
                original_transaction_ids = IAPReceiptHistory2.objects.filter(original_transaction_id=_original_transaction_id)
                if original_transaction_ids.exists():
                    context['reason'] = 'duplicated original_transaction_id'
                    context['original_transaction_id'] = _original_transaction_id
                    _track(IAP_VERIFY_ERROR, context)
                    return
                # 通过original_transaction_id防止重复发货 END
            except IndexError:
                context['reason'] = 'no last_in_app found'
                _track(IAP_VERIFY_ERROR, context)
                return
                        
            try:
                bundle_id = response.receipt['bundle_id']
            except:
                bundle_id = None

            if not bundle_id:
                try:
                    bundle_id = last_in_app.bid
                except AttributeError as _:
                    bundle_id = None
            
            if not bundle_id:
                context['reason'] = 'bundle_id is empty'
                _track(IAP_VERIFY_ERROR, context)
                return
            else:
                package_names = app.package_names
                try:
                    package_names_info = json.loads(package_names)
                except Exception as e:
                    context['reason'] = 'bundle_id not configured properly'
                    _track(IAP_VERIFY_ERROR, context)
                    return
                
                if bundle_id not in package_names_info: # 首先，确保包名是合法的
                    context['reason'] = 'invalid bundle_id'
                    _track(IAP_VERIFY_ERROR, context)
                    return
                else:
                    # 包名（bundle_id）确定是合法的，就要再进一步从product_id（bundleid-currency-goodid-realmoney）中获取到，此支付订单的真实的订单价格
                    SEP = '_'
                    product_id = last_in_app.product_id
                    try:
                        _bundleid, _currency, _goodid, realmoney = product_id.split(SEP)
                    except:
                        context['reason'] = 'cannot extract the 4 parts from product_id %s' % product_id
                        _track(IAP_VERIFY_ERROR, context)
                        return
                    
                    if bundle_id != _bundleid:
                        context['info'] = 'bundle_id from iap mismatch bundle_id extracted from product_id %s %s' % (bundle_id, _bundleid)
                        _track(IAP_VERIFY_INFO, context)
                    try:
                        realmoney = float(realmoney) # 单位为元
                        real_amount = int(realmoney * 100) # 元转换为分
                    except Exception as _:
                        context['reason'] = 'error when reading realmony from product_id'
                        _track(IAP_VERIFY_ERROR, context)
                        return
            ###### 校验包名 END
            ###### 校验包的审核状态，如果过审，则禁用沙箱支付                          
            package_online = package_names_info[bundle_id]['production'] == '1'
            if not IS_SANDBOX:
                order_status = 'S'
            else:
                if not package_online:
                    order_status = 'SS'
                else:
                    NEED_NOTIFY = False # 如果已经上线，禁用沙箱支付
                    order_status = 'E' # 同时将订单状态设置为异常
            ###### 校验包的审核状态，如果过审，则禁用沙箱支付 END
            
            try:
                user = User.objects.get(id=userid)
            except User.DoesNotExist:
                context['reason'] = 'user not exists'
                _track(IAP_VERIFY_ERROR, context)
                return
            
            if pay_channel != '99': # 苹果iTunes支付
                context['reason'] = 'invalid pay_channel'
                _track(IAP_VERIFY_ERROR, context)
                return
            
            orders = UserGameOrder.objects.filter(game_order_id=app_order_id)
            if not orders.exists(): # 如果订单不存在，创建订单
                platform = 2 # 手游
                passthrough = kwargs.get('passthrough', '')
                game_callback_url = kwargs.get('game_callback_url', '')
                # 创建本地订单
                order = UserGameOrder.create_order(
                    user=user, real_amount=real_amount, currency=_currency, 
                    app=app, game_order_id=app_order_id,
                    amount=amount, callback_url=game_callback_url,
                    good_name=good_name, passthrough=passthrough,
                    platform=platform, pay_channel=pay_channel
                )
                # 本地系统为本订单生成trade id
                order.trade_id = uuid.uuid4().get_hex()
            else:
                order = orders[0]
            order.order_status = order_status # 根据上下文信息修改订单状态

            try: # 保存订单
                order.save()
                
                # 防止应用内购买重复刷单状态更新
                def _getattr(name):
                    try:
                        return getattr(last_in_app, name)
                    except AttributeError:
                        return None
                
                attr_names = ['quantity', 'product_id', 'transaction_id', 'purchase_date_ms', 'original_transaction_id', 'original_purchase_date_ms']
                attr_values = map(_getattr, attr_names)
                for item in zip(attr_names, attr_values):
                    setattr(iap_receipt_history, item[0], item[1])
                
                iap_receipt_history.bundle_id = bundle_id
                iap_receipt_history.trade_id = order.trade_id
                iap_receipt_history.is_sandbox = IS_SANDBOX
                iap_receipt_history.state = 0 # 当前处于未验证状态
                iap_receipt_history.save()
                # 防止应用内购买重复刷单状态更新 END
            except Exception as save_exc:
                context['info'] = 'failed to create local order'
                _track(IAP_VERIFY_INFO, context)
                # 虽然本地订单保存不成功，但是还是要通知U8服务器，故此处不返回
            
            if not NEED_NOTIFY:
                context['reason'] = 'sandbox receipt trying to buy in production envronment'
                _track(IAP_VERIFY_ERROR, context)
                return
            request_args = get_callback_arg_tuples(order, others=[('ProductID', product_id)]) # 获取回调参数，用于请求U8服务器
            request_query_str = '&'.join(['='.join(item) for item in request_args])
            pay_callback_url = app.pay_callback_url
            context['pay_callback_url'] = pay_callback_url # 日志记录
            parsed_u8_callback_url = urlparse.urlparse(pay_callback_url)
            new_u8_parsed_callback_url = urlparse.ParseResult(scheme=parsed_u8_callback_url.scheme, 
                                                   netloc=parsed_u8_callback_url.netloc,
                                                   path=parsed_u8_callback_url.path,
                                                   params=parsed_u8_callback_url.params,
                                                   query=request_query_str,
                                                   fragment=parsed_u8_callback_url.fragment)
            new_u8_callback_url = urlparse.urlunparse(new_u8_parsed_callback_url)
            callback_sign = get_signature(app.appsecret.encode('utf-8'), new_u8_callback_url)
            request_args.append(('Sign', callback_sign))
            args_map = dict(request_args)
            request_obj = urllib2.Request(pay_callback_url) # 创建请求对象
            request_obj.add_data(urllib.urlencode(args_map)) # 添加请求参数
                
            response = urllib2.urlopen(request_obj, timeout=settings.PAY_CALLBACK_TIMEOUT).read()
            response_map = json.loads(response)
            context['response_map'] = response_map # 日志记录
            if response_map['status'] == 'success':
                _track(REUQEST_U8, context)
                iap_receipt_history.state = 1 # 标记为验证成功
                iap_receipt_history.save()
                set_user_ispay_cache(app.appid, user.id, real_amount) # 设置付费标记
                event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                _track(event_name, context)
            else:
                iap_receipt_history.state = 2 # 标记为验证失败
                iap_receipt_history.save()
                raise U8ResponseException(response_map['description']) # 向外层传播本异常，以引入重试机制
        else:
            context['reason'] = 'iap endpoint return none zero code'
            _track(IAP_VERIFY_ERROR, context)
    except Exception as ee:
        # 有异常的情况下，重试机制介入
        raise self.retry(exc=ee, max_retries=settings.CELERY_TASK_RETRY_POLICY_MAX_RETRIES, countdown=settings.CELERY_TASK_RETRY_POLICY[self.request.retries])

@shared_task(bind=True, base=LogTask)
def pay_info2u8(self, pay_callback_url, args_map_json):
    '''向U8服务器回调支付宝支付成功信息'''
    event_name = settings.API_IMPORTANT_EVENTS.REUQEST_U8
    
    args_map = json.loads(args_map_json)
    request_obj = urllib2.Request(pay_callback_url)
    request_obj.add_data(urllib.urlencode(args_map))
    try:
        response = urllib2.urlopen(request_obj, timeout=settings.PAY_CALLBACK_TIMEOUT).read()
        response_map = json.loads(response)
        
        # 日志记录
        context = {}
        context['pay_callback_url'] = pay_callback_url
        context['args_map'] = args_map
        context['response_map'] = response_map
        _track(event_name, context)
        # 日志记录 END
        if response_map['status'] != 'success':
            raise U8ResponseException(response_map['description'])
    except Exception as ee:
        # 有异常的情况下，重试机制介入
        raise self.retry(exc=ee, max_retries=settings.CELERY_TASK_RETRY_POLICY_MAX_RETRIES, countdown=settings.CELERY_TASK_RETRY_POLICY[self.request.retries])

@shared_task(bind=True, base=LogTask)
def googlepay_info2u8(self, context, meta, appid, packagename, productid, token, userid, app_order_id, amount, game_callback_url, good_name, passthrough, platform):
    pay_channel = '96'
    context['pay_channel'] = pay_channel # google支付，代码96
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CREATED
    try:
        user = User.objects.get(id=userid)
        app = App.objects.get(appid=appid)
    except Exception:
        context['reason'] = 'user or app error'
        _track(event_name, context, meta)
    
    #创建本地订单
    order = UserGameOrder.create_order(
        user=user, app=app, game_order_id=app_order_id,
        amount=amount, real_amount=amount, 
        callback_url=game_callback_url,
        good_name=good_name, passthrough=passthrough,
        platform=platform, pay_channel=pay_channel
    )
    # 本地系统为本订单生成trade id
    trade_id = uuid.uuid4().get_hex()
    order.trade_id = trade_id
    order.order_status = "I" # 发起支付接口，状态设置为I：待支付
    order.save()
    
    event_name = settings.API_IMPORTANT_EVENTS.GOOGLE_PAY_VERIFY_INFO
    try:
        servertoken = googlepay_token_refresh(appid)
    except Exception:
        event_name = settings.API_IMPORTANT_EVENTS.GOOGLE_PAY_REFRESH_TOKEN
        context['reason'] = 'google refresh token error'
        _track(event_name, context, meta)
    try:
        purchaseState = googlepay_product_status(packagename, productid, token, servertoken)
    except Exception:
        event_name = settings.API_IMPORTANT_EVENTS.GOOGLE_PAY_VERIFY_ERROR
        context['reason'] = 'google server connect error'
        _track(event_name, context, meta)
    else:
        if str(purchaseState) == '0':
            event_name = settings.API_IMPORTANT_EVENTS.REUQEST_U8
            # 只有在订单状态是购买成功的情况下，通知U8服务器
            request_args = get_callback_arg_tuples(order, others=[('ProductID', '')])
            request_query_str = '&'.join(['='.join(item) for item in request_args])
            pay_callback_url = order.app.pay_callback_url
            parsed_u8_callback_url = urlparse.urlparse(pay_callback_url)
            new_u8_parsed_callback_url = urlparse.ParseResult(scheme=parsed_u8_callback_url.scheme, 
                                                           netloc=parsed_u8_callback_url.netloc,
                                                           path=parsed_u8_callback_url.path,
                                                           params=parsed_u8_callback_url.params,
                                                           query=request_query_str,
                                                           fragment=parsed_u8_callback_url.fragment)
            new_u8_callback_url = urlparse.urlunparse(new_u8_parsed_callback_url)
            callback_sign = get_signature(order.app.appsecret.encode('utf-8'), new_u8_callback_url)
            request_args.append(('sign', callback_sign))
            request_args_map = dict(request_args)
            request_obj = urllib2.Request(pay_callback_url)
            request_obj.add_data(urllib.urlencode(request_args_map))
            try:
                response = urllib2.urlopen(request_obj, timeout=6).read()
            except Exception:
                context['reason'] = 'u8 connect error'
                _track(event_name, context, meta)
            else:
                #若U8返回成功，则修改本地订单状态为S
                if json.loads(response)['status'] == 'success':
                    order.order_status = "S"
                    order.save()
                    event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                    _track(event_name, context, meta)
                else:
                    context['reason'] = 'u8 response is failed'
                    _track(event_name, context, meta)
        elif str(purchaseState) == '1':
            #订单状态是已取消
            context['reason'] = 'order state is cancelled'
            _track(event_name, context, meta)
        else:
            #理论上不会出现这种情况
            context['reason'] = 'order state error'
            _track(event_name, context, meta)

@shared_task(bind=True, base=LogTask)
def track(self, event_name, context=None, meta=None):
    try:
        _track(event_name, context, meta)
    except Exception as ee:
        raise self.retry(exc=ee, max_retries=3, countdown=7)

def _track(event_name, context=None, meta=None):
    if settings.MATRIX_SWITCH:
        settings.MATRIX_CLIENT.track(event_name, context, meta)
