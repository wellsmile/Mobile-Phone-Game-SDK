# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-10 07:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_auto_20160908_0414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usergameorder',
            name='pay_channel',
            field=models.CharField(db_index=True, default='', max_length=20, verbose_name='\u652f\u4ed8\u901a\u9053\uff08100:\u652f\u4ed8\u5b9d\uff1b99:\u82f9\u679c\u652f\u4ed8\uff1b98:\u94f6\u8054\u652f\u4ed8\uff09'),
        ),
    ]
