#coding=utf-8
import hashlib
import base64
import json
import urlparse
import time
import uuid
from operator import itemgetter

from django.conf import settings
from django.http import HttpResponse
from django.http.response import JsonResponse

from models import App, User, GamePayType, UserGameOrder ,ThirdPartyUser
from tasks import iap_verify_receipt, pay_info2u8, googlepay_info2u8

from utils.signature import get_signature

from utils.paycenter.alipay.alipay import build_params as alipay_build_params
from utils.paycenter.alipay.alipay import check_sign as alipay_check_sign

from utils.paycenter.unionpay.unionpay import build_params as unionpay_build_params
from utils.paycenter.unionpay.unionpay import check_sign as unionpay_check_sign

from utils.paycenter.wechatpay.wechatpay import build_params as wechatpay_build_params
from utils.paycenter.wechatpay.wechatpay import check_sign as wechatpay_check_sign
from utils.paycenter.wechatpay.wechatpay import build_resp as wechatpay_build_resp
from utils.paycenter.wechatpay.wechatpay import AppPayInfoNotExist as WeChat_AppPayInfoNotExist
from utils.paycenter.wechatpay.wechatpay import build_xml
from utils.paycenter.wechatpay.wechatpay import parse_xml

from utils.paycenter.iapppay.iapppay import build_params as iapppay_build_params
from utils.paycenter.iapppay.iapppay import check_sign as iapppay_check_sign
from utils.paycenter.iapppay.iapppay import parse_resp as iapppay_parse_resp
from utils.paycenter.iapppay.iapppay import get_dopay_resp as iapppay_dopay_resp

from utils.paycenter.molpay.molpay import build_params as mol_build_params
from utils.paycenter.molpay.molpay import build_resp as mol_build_resp
from utils.paycenter.molpay.molpay import build_sign as mol_build_sign
from utils.paycenter.molpay.molpay import check_order as mol_check_order
from utils.paycenter.molpay.molpay import AppPayInfoNotExist as MOLPay_AppPayInfoNotExist

from utils.paycenter.fenqilepay.fenqilepay import build_params as fenqile_build_params
from utils.paycenter.fenqilepay.fenqilepay import build_resp as fenqile_build_resp
from utils.paycenter.fenqilepay.fenqilepay import build_sign as fenqile_build_sign

from utils import sms
from utils.cache import set_user_ispay_cache, get_user_ispay_cache
from utils.logcenter import apitrack
from utils.logcenter import get_request_context
from utils.paycenter.callback.callback import get_callback_arg_tuples
from utils.usercenter.register.onekey_register import onekey_username_password
from utils.usercenter.login.thirdparty import ThirdPartyLogin
from utils.usercenter.login.exceptions import AlreadyBindThirdPartyError
from utils.usercenter.access import get_request_ip
from utils import idcard

def index(request):
    response = HttpResponse('Hello HeyiJoy')
    return response

def initial(request):
    '''用户开启应用的时候初始化请求，检测更新'''
    parameters_getter = itemgetter('appid', 'appkey', 'version_code')
    appid, appkey, version_code = parameters_getter(request.GET)
    
    try:
        app = App.objects.get(appid=appid, appkey=appkey)
    except App.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '应用不存在'})
    
    # fixed values
    payload = {'up_sms': '', 'down_sms': '', 'probability': '', 'name_register': False, 'register_plan': '2', 'phone_register': False}
    payload['version_code'] = version_code # 用来判断是否是最新版本，是否需要升级，是一个整型数，比如 1，2，3..
    payload['latest_version_desc'] = app.latest_version_desc # 如果需要升级，升级的描述信息，用于呈现给用户
    payload['version_name'] = app.version_name # 用户看到的版本信息，比如: 3.0.1
    version_code = int(version_code)
    if version_code == app.latest_version_code:
        payload['is_update'] = False
    else:
        payload['is_update'] = True
        payload['app_size'] = app.app_size
        support_version_codes = [int(x) for x in app.support_version_code_list.split(',')]
        if version_code in support_version_codes: # 判断是否需要强制用户升级APP
            payload['force_update'] = '0'
        else:
            payload['force_update'] = '1'
    payload['pay_type'] = [item.identifier for item in app.pay_type.all() if item.status == 1]
    payload['download_link'] = app.download_link
    
    # 把is_update和force_update都设置为False
    payload['is_update'] = False
    payload['force_update'] = '0'
    # 把is_update和force_update都设置为False END
        
    # 添加附加信息
    google, facebook, cp_version, weibo, wechat, qq, real_name_authentication, real_name_authentication_pay = '', '', '', '', '', '', 'on', 'on'
    bundle_id = request.GET.get('bundle_id', None)
    if bundle_id:
        package_names = app.package_names
        try:
            package_names_info = json.loads(package_names)
        except:
            package_names_info = None
        
        if package_names_info:
            bundle_id_info = package_names_info.get(bundle_id, None)
            if bundle_id_info:
                google = bundle_id_info.get('google', '')
                facebook = bundle_id_info.get('facebook', '')
                weibo = bundle_id_info.get('weibo', '')
                wechat = bundle_id_info.get('wechat', '')
                qq = bundle_id_info.get('qq', '')
                cp_version = bundle_id_info.get('cp_version', '')
                real_name_authentication = bundle_id_info.get('authenticate', 'on')
                real_name_authentication_pay = bundle_id_info.get('authenticate_pay', 'on')
    payload['cp_google'] = google
    payload['cp_facebook'] = facebook
    payload['cp_weibo'] = weibo
    payload['cp_wechat'] = wechat
    payload['cp_qq'] = qq
    payload['cp_version'] = cp_version
    payload['authenticate'] = real_name_authentication
    payload['authenticate_pay'] = real_name_authentication_pay
    # 添加附加信息 END
    
    _payload = {'status': 'success', 'server_time': int(time.time())}
    _payload.update(payload)
    return JsonResponse(_payload)

def nick_register(request):
    '''快速注册'''
    context, meta = get_request_context(request) # 记录日志使用
    
    parameters_getter = itemgetter('username', 'password')
    username, password = parameters_getter(request.POST)
    
    imei = request.POST.get('imei', '')
    phone = request.POST.get('phone', '')
    appkey = request.POST.get('appkey', '')
    guid = request.POST.get('guid', '')
    
    register_way = request.POST.get('register_way', '0')
    extra_data = {}
    
    username = username.lower()
    if register_way == '1':
        # 一键注册功能需要服务器生成用户名和密码，并保证用户名的唯一性
        username, password =  onekey_username_password()
        extra_data['password'] = password
    
    try:
        user = User(username=username)
        user.set_password(password)
        uid = uuid.uuid4().hex #  生成唯一的uid
        user.id = uid
        user.imei = imei
        user.phone = phone
        user.guid = guid
        user.save()
    except Exception as e:
        # 记录日志
        event_name = settings.API_IMPORTANT_EVENTS.NICK_REGISTER_EXCEPTION
        context['exception'] = str(e)
        apitrack(event_name, 
                 context, 
                 meta)
        # 记录日志 END
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户已经存在'})
    
    sessionid = User.generate_sessionid(user.id, appkey)
    User.set_sessionid(uid, sessionid, 7200)
    
    lifecode = hashlib.md5(user.password_hash).hexdigest()
    success_data = {'status': 'success', 
                    'username': user.username, 
                    'sessionid': sessionid, 
                    'isNew': '1', 
                    'userid': user.id,
                    'lifecode': lifecode}
    success_data.update(extra_data)
    return JsonResponse(success_data)

def login(request):
    '''通过用户名和密码登录'''
    parameters_getter = itemgetter('username', 'password', 'appkey')
    username, password, appkey = parameters_getter(request.POST)
    username = username.lower()
    
    ok = False # 用户是否合法的标识
    thirdparty = request.POST.get('thirdparty', None)
    thirdparty_credential = request.POST.get('thirdparty_credential', None)
    appid = request.POST.get('appid', '')
    goto3rd = request.POST.get('goto3rd', 'f')
    lifecode = request.POST.get('lifecode', None)
    
    if thirdparty: # 使用三方登录
        user = None
        if goto3rd == 't' and thirdparty_credential:
            try:
                session_user = User.objects.get(username=username) # 如果提供了goto3rd，说明前端要将当前的游客账号绑定到第三方登陆渠道上
            except User.DoesNotExist:
                return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户名错误'})
            server_lifecode = hashlib.md5(session_user.password_hash).hexdigest()
            if server_lifecode != lifecode:
                return JsonResponse({'status': 'failed', 'code': -5, 'desc': '非法请求'})
            try:
                thirdpartyLogin = ThirdPartyLogin(appid, thirdparty, thirdparty_credential, session_user) # 通过所有检测之后，尝试绑定用户
                user = thirdpartyLogin.user()
            except AlreadyBindThirdPartyError:
                return JsonResponse({'status': 'failed', 'code': -6, 'desc': '用户已经绑定三方登陆'})
        elif thirdparty_credential:
            thirdpartyLogin = ThirdPartyLogin(appid, thirdparty, thirdparty_credential)
            user = thirdpartyLogin.user()
        else:
            try:
                session_user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户名错误'})
            server_lifecode = hashlib.md5(session_user.password_hash).hexdigest()
            if server_lifecode != lifecode:
                return JsonResponse({'status': 'failed', 'code': -5, 'desc': '非法请求'})
            user = session_user
            
        ok = user is not None
    else: # 使用账户密码登录,手机号也可以作为用户名
        by_username_user_exists = User.objects.filter(username=username).exists()
        by_phone_user_exists = User.objects.filter(phone=username).exists() if not by_username_user_exists else False
        if by_username_user_exists:
            user = User.objects.get(username=username)
        elif by_phone_user_exists:
            user = User.objects.get(phone=username)
        else:
            return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户名错误'})
        ok = user.check_password(password)
        if not ok: # 尝试使用lifecode登陆
            if lifecode:
                server_lifecode = hashlib.md5(user.password_hash).hexdigest()
                if server_lifecode == lifecode: # 如果lifecode合法，也认为用户登陆成功
                    ok = True

    if ok:
        if user.state != 0:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '账号异常'})
        sessionid = User.generate_sessionid(user.username, appkey)
        User.set_sessionid(user.id, sessionid, 7200)
        isbind = (user.phone != '') and (user.phone is not None)
        bind3rd = ThirdPartyLogin.bind_state(user) or ''
        lifecode = hashlib.md5(user.password_hash).hexdigest() # 从一定程度可以取代密码，用于需要来回传递密码，但是明文密码在服务器端又不存在的应用场景
        ispay = True if get_user_ispay_cache(appid, user.id) else False
        thirdpartyuserinfo = ''
        if thirdparty == 'wechat':
            # [微信,]登录的时候，需要额外返给前端三方平台上的用户信息
            thirdpartyuserobj = ThirdPartyUser.objects.get(user_id=user.id)
            thirdpartyuserinfo = thirdpartyuserobj.extra_info
            
        # 这里取一下用户是不是已经实名认证了
        authenticate = False
        if user.auth_name or user.auth_idcard: # 如果该用户已经实名认证过
            authenticate = True
        else:
            authenticate = False
        
        return JsonResponse({'status': 'success', 
                             'username': user.username, 
                             'sessionid': sessionid, 
                             'userid': user.id, 
                             'isbind': isbind, 
                             'phone': user.phone,
                             'bind3rd': bind3rd,
                             'lifecode': lifecode,
                             'ispay': ispay, 
                             'thirdpartyuserinfo': thirdpartyuserinfo,
                             'authenticate': authenticate})  
    else:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '请输入正确密码'})

def bindthirdparty(request):
    '''登录游客账户后，尝试绑定三方账户'''      
    parameters_getter = itemgetter('username', 'password', 'appid', 'thirdparty', 'thirdparty_credential')
    username, password, appid, thirdparty, thirdparty_credential = parameters_getter(request.POST)
    username = username.lower()
    try:
        session_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户名错误'})
    ok = session_user.check_password(password)
    if not ok:
        return JsonResponse({'status': 'failed', 'code': -5, 'desc': '非法请求'})
    try:
        thirdpartyLogin = ThirdPartyLogin(appid, thirdparty, thirdparty_credential, session_user) # 通过所有检测之后，尝试绑定用户
        user = thirdpartyLogin.user()
        if user is not None:
            return JsonResponse({'status': 'success', 'desc': '绑定三方账号成功'})
        else:
            return JsonResponse({'status': 'failed', 'code': -7, 'desc': '绑定三方账号失败'})
    except AlreadyBindThirdPartyError:
        return JsonResponse({'status': 'failed', 'code': -6, 'desc': '用户已经绑定三方登陆'})
    
def touristlogin(request):
    '''专为海外游客找回准备，是一个特殊的登录过程，当用户已经绑定过三方账号时拒绝登录，登录成功仅仅返回success'''
    parameters_getter = itemgetter('username', 'password', 'appkey', 'appid')
    username, password, appkey ,appid = parameters_getter(request.POST)
    username = username.lower()
    lifecode = request.POST.get('lifecode', None)
    
    ok = False # 用户是否合法的标识
    
    # 使用账户密码登录,手机号也可以作为用户名
    by_username_user_exists = User.objects.filter(username=username).exists()
    by_phone_user_exists = User.objects.filter(phone=username).exists() if not by_username_user_exists else False
    if by_username_user_exists:
        user = User.objects.get(username=username)
    elif by_phone_user_exists:
        user = User.objects.get(phone=username)
    else:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户名错误'})
    ok = user.check_password(password)
    if not ok: # 尝试使用lifecode登陆
        if lifecode:
            server_lifecode = hashlib.md5(user.password_hash).hexdigest()
            if server_lifecode == lifecode: # 如果lifecode合法，也认为用户登陆成功
                ok = True
                
    if ok:
        if user.state != 0:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '账号异常'})
        bind3rd = ThirdPartyLogin.bind_state(user) or ''
        if bind3rd == 'facebook':
            return JsonResponse({'status': 'failed', 'code': -5, 'desc': '账号已绑定facebook'})
        if bind3rd == 'google':
            return JsonResponse({'status': 'failed', 'code': -6, 'desc': '账号已绑定google'})
        else:
            sessionid = User.generate_sessionid(user.username, appkey)
            User.set_sessionid(user.id, sessionid, 7200)
            isbind = (user.phone != '') and (user.phone is not None)
            lifecode = hashlib.md5(user.password_hash).hexdigest() # 从一定程度可以取代密码，用于需要来回传递密码，但是明文密码在服务器端又不存在的应用场景
            ispay = True if get_user_ispay_cache(appid, user.id) else False
            return JsonResponse({'status': 'success', 
                                 'username': user.username, 
                                 'sessionid': sessionid, 
                                 'userid': user.id, 
                                 'isbind': isbind, 
                                 'phone': user.phone,
                                 'bind3rd': bind3rd,
                                 'lifecode': lifecode,
                                 'ispay': ispay})
    else:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '密码错误'})
                
def logout(request):
    '''注销用户'''
#     sessionid = request.POST.get('sessionid')
#     User.del_sessionid(sessionid)
    return JsonResponse({'status': 'success'})

def repassword(request):
    '''用户修改密码'''
    parameters_getter = itemgetter('username', 'userid', 'password', 'newpassword')
    username, userid, password, newpassword = parameters_getter(request.POST)
    username = username.lower()  
    try:
        user = User.objects.get(id=userid, username=username) # 根据用户ID和用户名找到对应的用户对象
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户不存在'}) # 如果用户不存在，告知前端
    
    ok = user.check_password(password)
    if ok:
        try:
            user.set_password(newpassword)
            user.save()
            isbind = (user.phone != '') and (user.phone is not None)
            return JsonResponse({'status': 'success', 'username': user.username, 'sessionid': None, 'userid': user.id, 'isbind': isbind})
        except Exception as _:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '数据库保存失败'})
    else:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '旧密码错误'})

def request_verifycode(request):
    '''用户请求下发短信，用来绑定手机'''
    context, meta = get_request_context(request) # 记录日志使用
    parameters_getter = itemgetter('username', 'userid', 'phone')
    username, userid, phone = parameters_getter(request.POST)
    username = username.lower()
    # 限定：一个手机号只能够绑定到一个用户上，用户名和手机号必需一一对应
    user = User.objects.filter(phone=phone)
    if user.exists():
        return JsonResponse({'status': 'failed', 'code': -4, 'desc': '您的手机号已被绑定'})
    
    try:
        _ = User.objects.get(id=userid, username=username)
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户不存在'})
    
    verifycode = User.generate_verifycode()

    code, _ = sms.AliDayuSMS.send(verifycode, '本游戏', phone, 
                                         sms_free_sign_name=settings.SMS_BIND_PHONE_FREE_SIGN_NAME, 
                                         sms_template_code=settings.SMS_BIND_PHONE_TEMPLATE_CODE)
    event_name = settings.API_IMPORTANT_EVENTS.REQUEST_SMS
    context['phone'] = phone # 记录日志
    context['verifycode'] = verifycode # 记录日志
    context['sp'] = 'dayu' # 记录日志
    context['purpose'] = 'bind phone' # 记录日志
    context['code'] = code # 记录日志
    apitrack(event_name, context, meta) # 记录日志
    
    if code == 0:
        duration = 30 * 60 # 短信有效期
        info_duration = 86400 # 本条信息在缓存中保存的期限，默认一天，如果超过一天，则视为从未发送过短信
        expire_at = int(time.time()) + duration
        verifycode_info = '%s:%s' % (verifycode, expire_at) # 相关信息序列化到一个字符串中
        User.save_verifycode(verifycode_info, phone, info_duration)
        return JsonResponse({'status': 'success', 'duration': duration})   
    else:
        if code == 15:
            return JsonResponse({'status': 'failed', 'code': -3, 'desc': '短信请求过于频繁，请稍后再试'})
        else:
            return JsonResponse({'status': 'failed', 'code': -100, 'desc': '系统错误，请稍后再试'})

def bindphone(request):
    '''用户已经收到验证码短信，此时请求服务器来完成绑定手机的最后一步'''
    parameters_getter = itemgetter('username', 'userid', 'verifycode', 'phone')
    username, userid, _verifycode, phone = parameters_getter(request.POST)
    username = username.lower()
    try:
        user = User.objects.get(id=userid, username=username)
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '用户不存在'})

    # 限定：一个手机号只能够绑定到一个用户上，用户名和手机号必需一一对应
    phone_user = User.objects.filter(phone=phone)
    if phone_user.exists():
        return JsonResponse({'status': 'failed', 'code': -7, 'desc': '您的手机号已被绑定'})
    
    server_verifycode_info = User.get_verifycode(phone)
    if server_verifycode_info is not None:
        server_verifycode, expire_at = server_verifycode_info.split(':')
        if time.time() > int(expire_at):
            return JsonResponse({'status': 'failed', 'code': -5, 'desc': '验证码已过期'})
    else:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '请先发送验证码'})
    
    if _verifycode == str(server_verifycode): # 用户正确输入了验证码，将手机号信息写入到用户的资料中
        user.phone = phone
        try:
            user.save()
            return JsonResponse({'status': 'success', 'desc': '手机绑定成功'})
        except Exception as _:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '数据库保存失败'})
    else:
        return JsonResponse({'status': 'failed', 'code': -6, 'desc': '验证码错误'})

def request_verifycode_resetpassword(request):
    '''请求下发短信以用于重置密码'''
    context, meta = get_request_context(request) # 记录日志使用
    phone = request.POST.get('phone')
    phone_format_ok = settings.PHONE_FORMAT_REGEX.match(phone)
    if not phone_format_ok:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '手机号格式错误'})
    
    phone_users = User.objects.filter(phone=phone)
    if not phone_users.exists():
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '此手机号未绑定任何帐号，请确保您提供的手机号是您之前绑定过的手机号'})
    
    verifycode = User.generate_verifycode() # 生成验证码
    code, _ = sms.AliDayuSMS.send(verifycode, '合乐智趣', phone, 
                                         sms_free_sign_name=settings.SMS_RESET_PASSWORD_FREE_SIGN_NAME, 
                                         sms_template_code=settings.SMS_RESET_PASSWORD_TEMPLATE_CODE)  
    
    event_name = settings.API_IMPORTANT_EVENTS.REQUEST_SMS
    context['phone'] = phone # 记录日志
    context['verifycode'] = verifycode # 记录日志
    context['sp'] = 'dayu' # 记录日志
    context['purpose'] = 'reset password' # 记录日志
    context['code'] = 'code' # 记录日志    
    apitrack(event_name, context, meta) # 记录日志
    
    if code == 0:
        duration = 30 * 60 # 短信有效期
        info_duration = 86400 # 本条信息在缓存中保存的期限，默认一天，如果超过一天，则视为从未发送过短信
        expire_at = int(time.time()) + duration
        verifycode_info = '%s:%s' % (verifycode, expire_at) # 相关信息序列化到一个字符串中
        key = 'RESETPASS_%s' % phone
        User.save_verifycode(verifycode_info, key, info_duration)
        return JsonResponse({'status': 'success', 'duration': duration})   
    else:
        if code == 15:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '短信请求过于频繁，请稍后再试'})
        else:
            return JsonResponse({'status': 'failed', 'code': -100, 'desc': '系统错误，请稍后再试'})

def resetpassword(request):
    phone = request.POST.get('phone')
    _verifycode = request.POST.get('verifycode')
    newpassword = request.POST.get('newpassword')
    
    phone_format_ok = settings.PHONE_FORMAT_REGEX.match(phone)
    if not phone_format_ok:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '手机号格式错误'})
    
    phone_users = User.objects.filter(phone=phone)
    if not phone_users.exists():
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '此手机号未绑定任何帐号，请确保您提供的手机号是您之前绑定过的手机号'})
    
    phone_user = phone_users[0]
    key = 'RESETPASS_%s' % phone
    server_verifycode_info = User.get_verifycode(key)
    if server_verifycode_info is not None:
        server_verifycode, expire_at = server_verifycode_info.split(':')
        if time.time() > int(expire_at):
            return JsonResponse({'status': 'failed', 'code': -5, 'desc': '验证码已过期'})
    else:
        return JsonResponse({'status': 'failed', 'code': -7, 'desc': '请先发送验证码'})
    
    if _verifycode == str(server_verifycode): # 如果用户输入了正确的验证码，将用户的密码重置成用户的新密码
        try:
            phone_user.set_password(newpassword)
            phone_user.save()
            return JsonResponse({'status': 'success', 'desc': '重置密码成功'})
        except:
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '数据库保存失败'})
    else:
        return JsonResponse({'status': 'failed', 'code': -6, 'desc': '验证码错误'})

def user_information(request):
    '''用户信息获取'''
    parameters_getter = itemgetter('sessionid', 'appkey', 'sign')
    sessionid, appkey, sign = parameters_getter(request.POST)
    try:
        app = App.objects.get(appkey=appkey)
    except App.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': 'app not exists'})
    
    # make sign
    sign_content = 'appkey={}&sessionid={}'.format(appkey, sessionid)
    sign_key = app.appsecret
    sign_real = get_signature(sign_key.encode('utf-8'), sign_content)
    if sign != sign_real:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': 'wrong signature'})
    
    userid = User.get_uid_by_session(sessionid)
    try:
        user = User.objects.get(id=userid)
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -4, 'desc': 'user not exists'})
    
    return JsonResponse({'status': 'success', 'userid': user.id, 'username': user.username, 'phone': user.phone})

def user_profile(request):
    parameters_getter = itemgetter('appkey', 'userid', 'sign')
    appkey, userid, sign = parameters_getter(request.POST)
    
    try:
        app = App.objects.get(appkey=appkey)
    except App.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': 'app not exists'})
    
    sign_content = 'appkey={}&userid={}'.format(appkey, userid)
    sign_key = app.appsecret
    sign_real = get_signature(sign_key.encode('utf-8'), sign_content)
    
    if sign != sign_real:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': 'wrong signature'})
    
    try:
        user = User.objects.get(id=userid)
    except User.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -4, 'desc': 'user not exists'})
    
    return JsonResponse({'status': 'success', 'userid': user.id, 'username': user.username, 'phone': user.phone})

def real_name_authentication(request):
    parameters_getter = itemgetter('userid', 'auth_name', 'auth_idcard') # 接收前端的参数
    userid, auth_name, auth_idcard = parameters_getter(request.POST)
    
    try:
        user = User.objects.get(id=userid)
    except User.DoesNotExist: # 如果该用户不存在
        return JsonResponse({'status': 'failed', 'code': -4, 'desc': '该用户不存在'}) #user not exists
    
    if user.auth_name or user.auth_idcard: # 如果该用户已经实名认证过
        return JsonResponse({'status': 'failed', 'code': -9, 'desc': '该用户已经实名认证过'}) #auth info has exists
    
    auth_idcard_valid = False
    
    # 此处填写验证身份证号准确性的逻辑
    
    if idcard.checkIdcard(auth_idcard): #如果身份证验证已经通过
        auth_idcard_valid = True
    
    # 此处填写验证姓名准确性的逻辑
    
    # 若验证通过，修改auth_idcard_valid为True
    
    if auth_idcard_valid: # 信息有效，存入数据库
        user.auth_name = auth_name
        user.auth_idcard = auth_idcard
        user.save()
        return JsonResponse({'status': 'success', 'desc': '实名认证信息已存储'})
    else: # 信息无效
        return JsonResponse({'status': 'failed', 'code': -10, 'desc': '身份证号无效'}) #auth info is invalid
    
#### 以下实现支付相关的API
def verify_receipt(request):
    '''验证支付结果，包含Itunes相关的验证，专门为苹果支付准备'''
    # 以下是苹果支付相关的验证过程需要的参数
    params_getter = itemgetter('verify_from', 'appid', 'amount', 'app_order_id', 'good_name', 'pay_channel', 'userid', 'raw_data')
    verify_from, appid, amount, app_order_id, good_name, pay_channel, userid, raw_data = params_getter(request.POST)
    # 发送到任务队列处理
    iap_verify_receipt.apply_async(args = [verify_from, appid, amount, app_order_id, good_name, pay_channel, userid], kwargs={'raw_data': raw_data})
    return JsonResponse({'status': 'success', 'desc': '服务器已接受你的验证请求'})

def verify_googlepay(request):
    '''为google支付准备，接收sdk请求并验证订单状态，若为已购买则通知U8发货'''
    parameters_getter = itemgetter('appid', 'packagename', 'productid', 'token', 
                                   'userid', 'app_order_id', 'amount', 'game_callback_url', 'good_name', 'passthrough')
    appid, packagename, productid, token, userid, app_order_id, amount, game_callback_url, good_name, passthrough = parameters_getter(request.POST)
    # 发送到任务队列处理
    if request.POST.has_key('platform'):
        platform = request.POST.get('platform')
    else:
        platform = 2
    context, meta = get_request_context(request)
    googlepay_info2u8.apply_async(args = [context, meta, appid, packagename, productid, token, userid, app_order_id, amount, game_callback_url, good_name, passthrough, platform])
    return JsonResponse({'status': 'success', 'desc': '服务器已接受你的验证请求'})

def check_apporderid(request):
    '''验证订单是否已经存在'''
    parameters_getter = itemgetter('appid', 'app_order_id')
    appid, app_order_id = parameters_getter(request.POST)
    try:
        app = App.objects.get(appid=appid)
        game_pay_types = GamePayType.objects.filter(game=app, status=1, type__status=1)
        if game_pay_types.exists():
            pay_list = [one.type.identifier for one in game_pay_types]
        else:
            pay_list = ['alipay']
        
        order = UserGameOrder.objects.filter(game_order_id=app_order_id)
        if order.exists():
            return JsonResponse({'status': 'failed', 'code': -4, 'desc': '订单ID已存在', 'pay_types': pay_list})
        else:
            return JsonResponse({'status': 'success', 'desc': '本订单ID可使用', 'pay_types': pay_list})
    except App.DoesNotExist:
        return JsonResponse({'status': 'failed', 'code': -2, 'desc': '游戏ID错误'})
    except Exception as e:
        return JsonResponse({'status': 'failed', 'code': -3, 'desc': '未知异常'})
    
def do_pay(request):
    '''发起付费接口，支持：
    支付宝：alipay 100
    苹果内购：iap 99
    银联支付：unionpay 98
    微信支付：wechatpay 97
    谷歌支付：googlepay(不调用此接口) 96
    腾讯支付：tencentpay(已删除) 95
    爱贝支付：iapppay 94
  MOL支付：molpay 93
    分期乐支付：fenqilepay 92
    '''
    context, meta = get_request_context(request) # 记录日志使用
    parameters_getter = itemgetter('appid', 'amount', 'app_order_id', 'game_callback_url', 'good_name', 'pay_channel', 'userid')
    appid, amount, app_order_id, game_callback_url, good_name, pay_channel, userid = parameters_getter(request.POST)
    amount = int(float(amount))
    
    passthrough = request.POST.get('passthrough', '')
    
    user = User.objects.get(id=userid)
    app = App.objects.get(appid=appid)
    
    orders = UserGameOrder.objects.filter(game_order_id=app_order_id)
    if orders.exists():
        return JsonResponse({'status': 'failed', 'code':-2, 'desc': '重复的订单号'})
    
    productid = request.POST.get('productid', '')
    
    platform = 2 # 手游
    #创建本地订单
    order = UserGameOrder.create_order(
        user=user, app=app, game_order_id=app_order_id,
        amount=amount, real_amount=amount, 
        callback_url=game_callback_url,
        good_name=good_name, passthrough=passthrough,
        platform=platform, pay_channel=pay_channel,
        productid=productid
    )
    
    # 本地系统为本订单生成trade id
    trade_id = uuid.uuid4().get_hex()
    order.trade_id = trade_id
    order.order_status = "I" # 发起支付接口，状态设置为I：待支付
    order.save()
    
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CREATED
    context['trade_id'] = order.trade_id # 记录日志
    apitrack(event_name, context, meta) # 记录日志
    
    spbill_create_ip = get_request_ip(request)
    
    if pay_channel == '100':# 支付宝
        params = alipay_build_params(trade_id, good_name, '', amount)
        results = {'trade_id': trade_id, 'channel_params': params}
        
    elif pay_channel == '98':# 银联
        params = unionpay_build_params(trade_id, amount)
        results = {'trade_id': trade_id, 'unionpay_pay_url': settings.UNIONPAY_PAY_URL, 'channel_params': params}
        
    elif pay_channel == '97':# 微信支付,相当于时序图第4,5,6,7步
        wechat_appid = request.POST.get('wechat_appid', None) # 微信支付时需要提供收款账户的微信appid，用于多账户支持
        if not wechat_appid:
            return JsonResponse({'status': 'failed', 'code': -1, 'desc': 'wechat_appid missing'})
        try:
            params_xml = wechatpay_build_params(str(productid), str(appid), str(wechat_appid), str(good_name), str(trade_id), str(amount), str(spbill_create_ip))
        except WeChat_AppPayInfoNotExist: # 如果appid+微信appid 取支付参数异常，很可能是后台没配，每个想要使用微信支付的app都需要配
            return JsonResponse({'status': 'failed', 'code': -3, 'desc': 'wechat_appid or appid error'})
        else:
            params = wechatpay_build_resp(appid, params_xml)
            results = {'trade_id': trade_id, 'channel_params': params}
            
    elif pay_channel == '94':# 爱贝
        iapppay_waresid = request.POST.get('iapppay_waresid', None) # 爱贝的特有参数，商品编号
        if not iapppay_waresid:
            return JsonResponse({'status': 'failed', 'code': -1, 'desc': 'iapppay_waresid missing'})
        params_str = iapppay_build_params(iapppay_waresid, trade_id, userid, productid, amount, good_name)
        resp_transdata = iapppay_dopay_resp(params_str)
        if resp_transdata.has_key('code'):
            return JsonResponse({'status': 'failed', 'desc': 'code:(iapppay return)' + str(resp_transdata['code']) })
        else:
            results = {'trade_id': trade_id, 'channel_params': {'transid': resp_transdata['transid']}}
            
    elif pay_channel == '93':# MOL
        mol_appid = request.POST.get('molpay_applicationcode', None) # 由于安卓ios支付参数不同，需要传入appcode去取secretcode
        if not mol_appid:
            return JsonResponse({'status': 'failed', 'code': -1, 'desc': 'molpay_applicationcode missing'})
        molpay_currency = request.POST.get('molpay_currency', None) # mol支付需要确认货币类型
        if not molpay_currency:
            return JsonResponse({'status': 'failed', 'code': -1, 'desc': 'molpay_currency missing'})
        
        try:
            params = mol_build_params(appid, mol_appid, trade_id, amount, molpay_currency, userid, description=good_name)
        except MOLPay_AppPayInfoNotExist:
            return JsonResponse({'status': 'failed', 'code': -3, 'desc': 'mol_appid or appid error'})
        else:
            # 如果是安卓端，不继续请求mol服务器
            isandroid = request.POST.get('isandroid', None)
            if isandroid:
                return JsonResponse({'status': 'success', 'desc': '该订单已经保存，并处于待支付状态', 'results': {'trade_id': trade_id}})
            
            paymentid, paymenturl = mol_build_resp(params)
            if paymentid and paymenturl:
                results = {'trade_id': trade_id, 'channel_params': {'paymentid': paymentid, 'paymenturl': paymenturl}}
            else:
                return JsonResponse({'status': 'failed', 'desc': 'molpay do pay error'})
    
    elif pay_channel == '92': # 分期乐
        params = fenqile_build_params(amount, trade_id, good_name, spbill_create_ip, productid)
        fenqile_resp = fenqile_build_resp(params)
        if str(fenqile_resp['result']) != '0':
            return JsonResponse({'status': 'failed', 'desc': 'fenqile do pay error:' + fenqile_resp['res_info']})
        results = {'trade_id': trade_id, 'channel_params': {'paymenturl': fenqile_resp['url']}}
            
    return JsonResponse({'status': 'success', 'desc': '该订单已经保存，并处于待支付状态', 'results': results})

def verify_alipay(request):
    '''支付宝会调用这个接口，通知关于订单的消息；
    此接口，会将这个订单的信息更新；
    随后，将异步地将相关的信息通知到U8服务器'''
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 100 # 支付宝支付，代码100
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR
    
    sign = request.POST.get('sign', None)
    if sign is None:
        return HttpResponse('missing sign')
    
    # 首先要确保，这个回调请求的合法性，只有在此请求合法的情况下才能进行下一步的操作
    first_value_getter = itemgetter(0)
    message = '&'.join(['='.join(kv) for kv in sorted([item for item in request.POST.iteritems() if item[0] not in ('sign','sign_type')], key=first_value_getter)])
    ok = alipay_check_sign(message, base64.decodestring(sign)) # 支付宝文档～第四步： 使用RSA的验签方法，通过签名字符串、签名参数（经过base64解码）及支付宝公钥验证签名。
    if ok: # 如果签名验证通过，说明这个请求是合法的，才能进一步处理
        trade_status = request.POST.get('trade_status', '')
        out_trade_no = request.POST.get('out_trade_no', '')
        try:
            order = UserGameOrder.objects.get(trade_id=out_trade_no)
            if order.order_status == 'I': # 只对处于“待支付”状态的订单进行处理
                if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                    order.order_status = 'S'
                    # 只有在成功的情况下，通知U8服务器
                    request_args = get_callback_arg_tuples(order, others=[('ProductID', '')]) # 获取回调参数，用于请求U8服务器
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
                    request_args_json = json.dumps(dict(request_args))
                    # 以下是在任务队列中异步通知U8服务器
                    pay_info2u8.apply_async(args = [order.app.pay_callback_url, request_args_json])
                    set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                    event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                    apitrack(event_name, context, meta)
                elif trade_status in ('TRADE_CLOSED', ):
                    order.order_status = 'C'
                    context['reason'] = 'order is cancel'
                    apitrack(event_name, context, meta)
                order.save() # 保存到数据库
            else:
                context['reason'] = 'order not in state I'
                apitrack(event_name, context, meta)
        except UserGameOrder.DoesNotExist:
            context['reason'] = 'missing local order'
            apitrack(event_name, context, meta)
            return HttpResponse('missing local order')
        except Exception as e:
            context['reason'] = str(e)
            apitrack(event_name, context, meta)
            return HttpResponse('failed')
        return HttpResponse('success') # 程序执行完后必须打印输出“success”（不包含引号）。如果商户反馈给支付宝的字符不是success这7个字符，支付宝服务器会不断重发通知，直到超过24小时22分钟。一般情况下，25小时以内完成8次通知（通知的间隔频率一般是：4m,10m,10m,1h,2h,6h,15h）；
    else:
        context['reason'] = 'invalid sign'
        apitrack(event_name, context, meta)
        return HttpResponse('invalid sign')

def verify_unionpay(request):
    '''
    银联会调用这个接口，通知关于支付结果的信息，
    本接口会将对应的订单的状态信息更新，
    并调用U8服务器异步通知U8服务器关于此订单的信息
    相关文档：None
    '''
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 98 # 银联支付，代码98
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR
    
    signature = request.POST.get('signature', None)
    if signature is None:
        return HttpResponse('missing signature')
    
    first_value_getter = itemgetter(0)
    message = '&'.join(['='.join(kv) for kv in sorted([item for item in request.POST.iteritems() if item[0] not in ('signature')], key=first_value_getter)])
    message_digest = hashlib.sha1(message).hexdigest()
    ok = unionpay_check_sign(message_digest, base64.decodestring(signature))
    if ok:
        resp_code = request.POST.get('respCode', '')
        out_trade_no = request.POST.get('orderId')
        try:
            order = UserGameOrder.objects.get(trade_id=out_trade_no)
            if order.order_status == 'I': # 只对处于“待支付”状态的订单进行处理
                if resp_code == '00' or resp_code == 'A6':
                    order.order_status = 'S'
                    # 只有在成功的情况下，通知U8服务器
                    request_args = get_callback_arg_tuples(order, others=[('ProductID', '')]) # 获取回调参数，用于请求U8服务器
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
                    request_args.append(('Sign', callback_sign))
                    request_args_json = json.dumps(dict(request_args))
                    # 以下是在任务队列中异步通知U8服务器
                    pay_info2u8.apply_async(args = [pay_callback_url, request_args_json])
                    order.save() # 保存到数据库
                    set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                    event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                    apitrack(event_name, context, meta)
            else:
                context['reason'] = 'order not in state I'
                apitrack(event_name, context, meta)
        except UserGameOrder.DoesNotExist:
            context['reason'] = 'missing local order'
            apitrack(event_name, context, meta)
            return HttpResponse('missing local order')
        except Exception as e:
            context['reason'] = str(e)
            apitrack(event_name, context, meta)
            return HttpResponse('failed')
        return HttpResponse('success')
    else:
        context['reason'] = 'invalid sign'
        apitrack(event_name, context, meta)
        return HttpResponse('invalid sign')

def unionpay_front(request):
    '''
    银联会调用这个接口，通知关于支付结果的信息；
    本接口会根据银联返回的通知信息，返回给用户一个支付结果页面；
    一开始可以使用非常简单的文字提示，后续可以美化相关的显示；
    '''
    signature = request.POST.get('signature', None)
    if signature is None:
        return HttpResponse('missing signature')
    
    first_value_getter = itemgetter(0)
    message = '&'.join(['='.join(kv) for kv in sorted([item for item in request.POST.iteritems() if item[0] not in ('signature')], key=first_value_getter)])
    message_digest = hashlib.sha1(message).hexdigest()
    ok = unionpay_check_sign(message_digest, base64.decodestring(signature))
    if ok:
        resp_code = request.POST.get('respCode', '')
        resp_msg = request.POST.get('respMsg')
        if resp_code == '00':
            return HttpResponse('支付成功')
        else:
            return HttpResponse('支付失败')
    else:
        return HttpResponse('非法的签名')

def verify_wechatpay(request):
    '''相当于时序图第16步
    Doc: https://pay.weixin.qq.com/wiki/doc/api/app/app.php?chapter=9_1#
                    微信会调用这个接口，通知关于订单的消息；
                    此接口给微信返回接收成功，并异步的通知U8服务器
    '''
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 97 # 微信支付，代码97
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR
    
    info_xml = build_xml({'return_code':'SUCCESS', 'return_msg':'OK'})
    if not wechatpay_check_sign(request.body):
        info = {'return_code':'FAIL', 'return_msg':'参数格式校验错误'}
        return HttpResponse(build_xml(info))
    else:# 接收合法的回调请求，异步的通知U8发货，并把本地订单状态改为S
        request_dict = parse_xml(request.body)
        productid = json.loads(request_dict['attach'])['productid']
        result_code = request_dict['result_code']
        out_trade_no = request_dict['out_trade_no']
        try:
            order = UserGameOrder.objects.get(trade_id=out_trade_no)
            if order.order_status == 'I': # 只对处于“待支付”状态的订单进行处理
                if result_code == 'SUCCESS':
                    order.order_status = 'S'
                    # 只有在成功的情况下，通知U8服务器
                    request_args = get_callback_arg_tuples(order, others=[('ProductID', productid)]) # 获取回调参数，用于请求U8服务器
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
                    request_args_json = json.dumps(dict(request_args))
                    # 以下是在任务队列中异步通知U8服务器
                    pay_info2u8.apply_async(args = [order.app.pay_callback_url, request_args_json])
                    set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                    event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                    apitrack(event_name, context, meta)
                elif result_code == 'FAIL':
                    order.order_status = 'C'
                    context['reason'] = 'order is cancel'
                    apitrack(event_name, context, meta)
                order.save() # 保存到数据库
            else:
                context['reason'] = 'order not in state I'
                apitrack(event_name, context, meta)
        except UserGameOrder.DoesNotExist:
            context['reason'] = 'missing local order'
            apitrack(event_name, context, meta)
            return HttpResponse(info_xml)
        except Exception as e:
            context['reason'] = str(e)
            apitrack(event_name, context, meta)
            return HttpResponse(info_xml)
        else:
            return HttpResponse(info_xml)
        
def verify_iapppay(request):
    '''
    Doc: https://www.iapppay.com/g-resultmsg.html
    接收爱贝回调，并通知u8服务器发货
    '''
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 94 # 爱贝支付，代码94
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR
    
    params_dict = iapppay_parse_resp(request.body)
    transdata = json.loads(params_dict['transdata'])
    
    sign = params_dict['sign']
    
    if not iapppay_check_sign(params_dict['transdata'], base64.b64decode(sign)):
        return HttpResponse('sign error')
    else:# 接收合法的回调请求，异步的通知U8发货，并把本地订单状态改为S
        productid = str(transdata['cpprivate'])
        result_code = str(transdata['result'])
        out_trade_no = str(transdata['cporderid'])
        try:
            order = UserGameOrder.objects.get(trade_id=out_trade_no)
            if order.order_status == 'I': # 只对处于“待支付”状态的订单进行处理
                if result_code == '0':
                    order.order_status = 'S'
                    # 只有在成功的情况下，通知U8服务器
                    request_args = get_callback_arg_tuples(order, others=[('ProductID', productid)]) # 获取回调参数，用于请求U8服务器
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
                    request_args_json = json.dumps(dict(request_args))
                    # 以下是在任务队列中异步通知U8服务器
                    pay_info2u8.apply_async(args = [order.app.pay_callback_url, request_args_json])
                    set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                    event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                    apitrack(event_name, context, meta)
                elif result_code == '1':
                    order.order_status = 'C'
                    context['reason'] = 'order is cancel'
                    apitrack(event_name, context, meta)
                else:
                    return HttpResponse('result code error')
                order.save() # 保存到数据库
            else:
                context['reason'] = 'order not in state I'
                apitrack(event_name, context, meta)
        except UserGameOrder.DoesNotExist:
            context['reason'] = 'missing local order'
            apitrack(event_name, context, meta)
            return HttpResponse('SUCCESS')
        except Exception as e:
            context['reason'] = str(e)
            apitrack(event_name, context, meta)
            return HttpResponse('SUCCESS')
        else:
            return HttpResponse('SUCCESS')
        
def verify_molpay(request):
    '''接收mol服务器的回调，检验无误后通知u8发货'''
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 93 # MOL支付，代码93
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR
    
    params_dict = request.POST.dict()
    out_trade_no = params_dict.get('referenceId', None)
    
    try:
        order = UserGameOrder.objects.get(trade_id=out_trade_no)
        appid = order.app.appid
        sign = params_dict.pop('signature')
        mol_appid = params_dict.get('applicationCode', None)
        try:
            serversign = mol_build_sign(appid, mol_appid, params_dict)
        except MOLPay_AppPayInfoNotExist:
            return HttpResponse('mol_appid or appid error')
        if not sign == serversign: # 验签
            return HttpResponse('sign error')
        if order.order_status == 'I': # 只对处于“待支付”状态的订单进行处理
            paymentid = params_dict.get('paymentId', None)
            result_code = mol_check_order(appid, mol_appid, out_trade_no, paymentid) or 'error' # 由于秘钥存储在设备上，需要查询订单确认是否支付成功
            if result_code == '00':
                order.order_status = 'S'
                # 只有在成功的情况下，通知U8服务器
                request_args = get_callback_arg_tuples(order, others=[('ProductID', order.productid)]) # 获取回调参数，用于请求U8服务器
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
                request_args_json = json.dumps(dict(request_args))
                # 以下是在任务队列中异步通知U8服务器
                pay_info2u8.apply_async(args = [order.app.pay_callback_url, request_args_json])
                set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                apitrack(event_name, context, meta)
            elif result_code == '99':
                order.order_status = 'C'
                context['reason'] = 'order is cancel'
                apitrack(event_name, context, meta)
            else:
                return HttpResponse('result code error')
            order.save() # 保存到数据库
        else:
            context['reason'] = 'order not in state I'
            apitrack(event_name, context, meta)
    except UserGameOrder.DoesNotExist:
        context['reason'] = 'missing local order'
        apitrack(event_name, context, meta)
        return HttpResponse('SUCCESS')
    except Exception as e:
        context['reason'] = str(e)
        apitrack(event_name, context, meta)
        return HttpResponse('SUCCESS')
    else:
        return HttpResponse('SUCCESS')
    
def verify_fenqilepay(request):
    context, meta = get_request_context(request) # 记录日志使用
    context['pay_channel'] = 92 # 分期乐支付，代码92
    event_name = settings.API_IMPORTANT_EVENTS.ORDER_CALLBACK_ERROR

    params_dict = json.loads(request.body)
    result = str(params_dict.get('result','-1'))
    try:
        if result == '0':
            sign = params_dict.pop('sign')
            server_sign = fenqile_build_sign(params_dict)
            if sign == server_sign:
                out_trade_no = params_dict.get('out_trade_no')
                order = UserGameOrder.objects.get(trade_id=out_trade_no)
                if order.order_status == 'I':
                    trans_status = params_dict.get('trans_status')
                    if str(trans_status) == '200':
                        order.order_status = 'S'
                        productid = params_dict.get('attach')
                        # 只有在成功的情况下，通知U8服务器
                        request_args = get_callback_arg_tuples(order, others=[('ProductID', productid)]) # 获取回调参数，用于请求U8服务器
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
                        request_args_json = json.dumps(dict(request_args))
                        # 以下是在任务队列中异步通知U8服务器
                        pay_info2u8.apply_async(args = [order.app.pay_callback_url, request_args_json])
                        set_user_ispay_cache(order.app.appid, order.user.id, order.real_amount)
                        event_name = settings.API_IMPORTANT_EVENTS.PAY_SUCCESS
                        apitrack(event_name, context, meta)
                    elif str(trans_status) == '300':
                        order.order_status = 'C'
                        context['reason'] = 'order is cancel'
                        apitrack(event_name, context, meta)
                    else:
                        return JsonResponse({"result":-1, "error_info":"trans_status is 100"})
                    order.save() # 保存到数据库
                else:
                    context['reason'] = 'order not in state I'
                    apitrack(event_name, context, meta)
            else:
                context['reason'] = 'sign error'
                apitrack(event_name, context, meta)
                return JsonResponse({"result":-1, "error_info":"sign_error"})
        else:
            return JsonResponse({"result":0})
    except UserGameOrder.DoesNotExist:
        context['reason'] = 'missing local order'
        apitrack(event_name, context, meta)
        return JsonResponse({"result":0})
    except Exception as e:
        context['reason'] = str(e)
        apitrack(event_name, context, meta)
        return JsonResponse({"result":0})
    else:
        return JsonResponse({"result":0})