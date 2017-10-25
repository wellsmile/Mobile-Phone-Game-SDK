# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-26 06:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20160826_0633'),
    ]

    operations = [
        migrations.RenameField(
            model_name='app',
            old_name='support_version_list',
            new_name='support_version_code_list',
        ),
        migrations.AddField(
            model_name='app',
            name='app_size',
            field=models.BigIntegerField(default=0, verbose_name='Size of the app'),
        ),
    ]
