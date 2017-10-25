#coding=utf-8
from django.contrib import admin

from models import App, PayType, GamePayType, User, UserGameOrder, ThirdPartyAppInfo, AppPayInfo

class AppAdmin(admin.ModelAdmin):
    search_fields = ('appid', 'appkey', 'appsecret', 'name')
    filter_horizontal = ('pay_type',)
    list_display = ('appid', 'name', 'appkey', 'appsecret', 'package_names', 'description', 'version_name', 'latest_version_code', 'create_at', 'update_at')
    ordering = ('-update_at', '-create_at')

class UserGameOrderAdmin(admin.ModelAdmin):
    search_fields = ('game_order_id', 'trade_id', 'user__id', 'app__appid')
    list_display = ('trade_id', 'game_order_id', 'amount', 'real_amount', 'currency', 'pay_channel', 'good_name', 'get_user_name', 'get_app_name', 'order_status', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def get_user_name(self, obj):
        '''用于展示的用户名'''
        return obj.user.username
    get_user_name.short_description = '用户名'
    
    def get_app_name(self, obj):
        '''用于展示交易所在的APP的名称'''
        return obj.app.name
    get_app_name.short_description = '应用名'

class UserAdmin(admin.ModelAdmin):
    search_fields = ('id', 'username', 'phone',)
    list_display = ('id', 'username', 'phone', 'create_at', 'register_at', 'state')
    ordering = ('-create_at',)

class PayTypeAdmin(admin.ModelAdmin):
    search_fields = ('name', 'identifier', 'status')
    list_display = ('name', 'identifier', 'seq', 'status')
    ordering = ('seq', 'status')

class GamePayTypeAdmin(admin.ModelAdmin):
    search_fields = ('status', 'game__name', 'type__name')
    list_display = ('status', 'get_app_name', 'get_type_name')
    
    def get_app_name(self, obj):
        return obj.game.name
    get_app_name.short_description = '应用名'
    
    def get_type_name(self, obj):
        return obj.type.name
    get_type_name.short_description = '支付类型名称'

class ThirdPartyAppInfoAdmin(admin.ModelAdmin):
    search_fields = ('app__name', 'thirdparty')
    list_display = ('get_app_name', 'thirdparty', 'info')
    
    def get_app_name(self, obj):
        return obj.app.name
    get_app_name.short_description = 'APP名'
    
admin.site.register(App, AppAdmin)
admin.site.register(PayType, PayTypeAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserGameOrder, UserGameOrderAdmin)
admin.site.register(GamePayType, GamePayTypeAdmin)
admin.site.register(ThirdPartyAppInfo, ThirdPartyAppInfoAdmin)
admin.site.register(AppPayInfo)