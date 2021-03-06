# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-28 08:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_auto_20170109_0939'),
    ]

    operations = [
        migrations.AddField(
            model_name='usergameorder',
            name='productid',
            field=models.CharField(default='', max_length=128, verbose_name='\u901a\u77e5U8\u53d1\u8d27\u65f6\u6240\u9700\u7684productid'),
        ),
        migrations.AlterField(
            model_name='apppayinfo',
            name='paytype',
            field=models.CharField(choices=[('wechatpay', 'wechatpay'), ('alipay', 'alipay'), ('tencentpay', 'tencentpay'), ('googlepay', 'googlepay'), ('unionpay', 'unionpay'), ('iap', 'iap'), ('iapppay', 'iapppay'), ('molpay', 'molpay')], max_length=64),
        ),
    ]
