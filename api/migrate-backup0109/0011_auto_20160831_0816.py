# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-31 08:16
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_auto_20160827_1154'),
    ]

    operations = [
        migrations.CreateModel(
            name='GamePayType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(verbose_name='\u72b6\u6001 0-\u5173\u95ed 1-\u5f00\u542f')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App', verbose_name='\u6e38\u620f')),
            ],
            options={
                'verbose_name': 'Game Pay Type',
                'verbose_name_plural': 'Game Pay Type',
            },
        ),
        migrations.CreateModel(
            name='UserGameOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(verbose_name='\u652f\u4ed8\u91d1\u989d\u5355\u4f4d(\u5206)')),
                ('trade_id', models.CharField(db_index=True, max_length=32, null=True, unique=True, verbose_name='\u652f\u4ed8\u4e2d\u5fc3\u8ba2\u5355id')),
                ('game_order_id', models.CharField(db_index=True, max_length=64, verbose_name='\u6e38\u620f\u5546\u8ba2\u5355id')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='\u521b\u5efa\u65f6\u95f4')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='\u6700\u540e\u66f4\u65b0\u65f6\u95f4')),
                ('int_date', models.IntegerField(db_index=True, verbose_name='\u6574\u5f62\u65e5\u671f 20150102')),
                ('callback_url', models.CharField(max_length=256, verbose_name='\u56de\u8c03\u5730\u5740')),
                ('pay_channel', models.CharField(db_index=True, default='', max_length=20, verbose_name='\u652f\u4ed8\u901a\u9053')),
                ('good_name', models.CharField(default='\u6e38\u620f\u9053\u5177', max_length=20, verbose_name='\u5546\u54c1\u540d\u79f0')),
                ('passthrough', models.CharField(default='', max_length=128, verbose_name='\u900f\u4f20\u53c2\u6570')),
                ('sign', models.CharField(default='', max_length=256, verbose_name='\u6570\u5b57\u7b7e\u540d')),
                ('platform', models.IntegerField(choices=[(1, 'TV'), (2, '\u624b\u6e38')], db_index=True, default=1, verbose_name='\u6e38\u620f\u5e73\u53f0')),
                ('notice_status', models.IntegerField(choices=[(0, '\u672a\u901a\u77e5'), (1, '\u6210\u529f'), (2, '\u5931\u8d25')], db_index=True, verbose_name='\u901a\u77e5cp\u72b6\u6001')),
                ('order_status', models.CharField(choices=[('I', '\u5f85\u4ed8\u6b3e'), ('S', '\u4ea4\u6613\u6210\u529f'), ('F', '\u4ea4\u6613\u5931\u8d25'), ('R', '\u9000\u6b3e'), ('C', '\u4ea4\u6613\u5173\u95ed')], db_index=True, max_length=2, verbose_name='\u8ba2\u5355\u72b6\u6001')),
                ('notice_desc', models.CharField(default='', max_length=256, verbose_name='\u901a\u77e5\u6e38\u620f\u670d\u52a1\u5546\u5931\u8d25\u539f\u56e0')),
                ('order_source', models.IntegerField(choices=[(1, '\u652f\u4ed8'), (2, '\u5145\u503c\u5e76\u652f\u4ed8')], default=1, verbose_name='\u8ba2\u5355\u6765\u6e90')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App')),
            ],
            options={
                'verbose_name': 'User Order',
                'verbose_name_plural': 'User Order',
            },
        ),
        migrations.AlterModelOptions(
            name='paytype',
            options={'verbose_name': 'Pay Type', 'verbose_name_plural': 'Pay Type'},
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(db_index=True, max_length=128, null=True, unique=True, verbose_name='User Name'),
        ),
        migrations.AddField(
            model_name='usergameorder',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.User'),
        ),
        migrations.AddField(
            model_name='gamepaytype',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.PayType', verbose_name='\u652f\u4ed8\u65b9\u5f0f'),
        ),
    ]
