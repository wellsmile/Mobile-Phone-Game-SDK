#coding=utf-8
'''
Created on Sep 11, 2016

@author: Felix
'''
import os
import OpenSSL
BASE_DIR = '/Users/Felix/Documents/workspace/apiserver'
PRODUCTION = False

# 银联支付相关配置
if PRODUCTION:
    UNIONPAY_CERTS_PATH = os.path.join(BASE_DIR, 'utils/paycenter/unionpay/certs')
    UNIONPAY_APP_PRIVATE_KEY_CERT_PASSWORD = '000000' # 商户私钥证书密码
else:
    UNIONPAY_CERTS_PATH = os.path.join(BASE_DIR, 'utils/paycenter/unionpay/certs_test')
    UNIONPAY_APP_PRIVATE_KEY_CERT_PASSWORD = '000000' # 商户私钥证书密码

# 商户私钥证书
UNIONPAY_APP_PRIVATE_KEY_CERT = os.path.join(UNIONPAY_CERTS_PATH, '700000000000001_acp.pfx') # PKCS12 format
UNIONPAY_PRIVATE_KEYSTORE = OpenSSL.crypto.load_pkcs12(open(UNIONPAY_APP_PRIVATE_KEY_CERT).read(), UNIONPAY_APP_PRIVATE_KEY_CERT_PASSWORD)
UNIONPAY_PRIVATE_KEY_OBJ = UNIONPAY_PRIVATE_KEYSTORE.get_privatekey()
UNIONPAY_CERT_OBJ = UNIONPAY_PRIVATE_KEYSTORE.get_certificate()
UIONPAY_CERT_ID = UNIONPAY_CERT_OBJ.get_serial_number()
# 银联公钥证书
UNIONPAY_PUBLIC_KEY_CERT = os.path.join(UNIONPAY_CERTS_PATH, 'verify_sign_acp.cer')
UNIONPAY_PUBLIC_KEYSTORE = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(UNIONPAY_PUBLIC_KEY_CERT).read())
UNIONPAY_PUBLIC_KEY_OBJ = UNIONPAY_PUBLIC_KEYSTORE.get_pubkey()

UNIONPAY_ACC_TYPE = '01'
UNIONPAY_ACCESS_TYPE='0'
UNIONPAY_BACK_URL = 'http://mainsdk.youku-game.com/game/verify_unionpay'
UNIONPAY_BIZ_TYPE = '000201'
UNIONPAY_CERT_ID = '%s' % UIONPAY_CERT_ID
UNIONPAY_CHANNEL_TYPE='07'
UNIONPAY_CURRENCY_CODE = '156'
UNIONPAY_ENCODING = 'UTF-8'
UNIONPAY_MER_ID = '700000000000001'
UNIONPAY_SIGN_METHOD = '01'
UNIONPAY_VERSION = '5.0.0'
UNIONPAY_TXN_TYPE = '01' # 交易类型：消费
UNIONPAY_TXN_SUBTYPE = '00' # 交易子类， 依据实际交易类型填写 默认取值:00

# 银联支付相关配置 END

if __name__ == '__main__':
    pass