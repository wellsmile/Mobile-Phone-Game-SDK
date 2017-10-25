# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-10-24 10:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_auto_20161022_0640'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gg_userid', models.CharField(max_length=128, unique=True)),
                ('extra_info', models.TextField(blank=True, null=True)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.User')),
            ],
        ),
        migrations.AlterField(
            model_name='fbuser',
            name='extra_info',
            field=models.TextField(blank=True, null=True),
        ),
    ]
