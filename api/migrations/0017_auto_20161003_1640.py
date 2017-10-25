# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-10-03 16:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_auto_20160921_0951'),
    ]

    operations = [
        migrations.CreateModel(
            name='IAPReceiptHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iap_digest', models.CharField(max_length=255, unique=True, verbose_name='\u82f9\u679c\u652f\u4ed8\u9a8c\u8bc1\u4e32\u7684md5\u503c')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterField(
            model_name='usergameorder',
            name='order_status',
            field=models.CharField(choices=[('I', '\u5f85\u4ed8\u6b3e'), ('S', '\u4ea4\u6613\u6210\u529f'), ('F', '\u4ea4\u6613\u5931\u8d25'), ('R', '\u9000\u6b3e'), ('C', '\u4ea4\u6613\u5173\u95ed'), ('SS', 'iTunes Sandbox\u4ea4\u6613\u6210\u529f')], db_index=True, max_length=2, verbose_name='\u8ba2\u5355\u72b6\u6001'),
        ),
    ]