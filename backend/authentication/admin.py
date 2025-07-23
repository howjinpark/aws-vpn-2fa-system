from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from .models import VPNGroupPolicy, UserTwoFactorAuth, VPNAccessLog

@admin.register(UserTwoFactorAuth)
class UserTwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'created_at', 'updated_at']
    list_filter = ['is_enabled', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['secret_key', 'created_at', 'updated_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('2FA 설정', {
            'fields': ('secret_key', 'is_enabled', 'backup_tokens')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VPNAccessLog)
class VPNAccessLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'client_ip', 'access_time', 'two_factor_verified', 'access_granted']
    list_filter = ['two_factor_verified', 'access_granted', 'access_time']
    search_fields = ['username', 'client_ip']
    readonly_fields = ['user', 'username', 'client_ip', 'access_time', 'two_factor_verified', 'access_granted']
    date_hierarchy = 'access_time'
    
    def has_add_permission(self, request):
        return False  # 로그는 수동으로 추가할 수 없음

@admin.register(VPNGroupPolicy)
class VPNGroupPolicyAdmin(admin.ModelAdmin):
    list_display = ['group', 'require_2fa', 'enable_time_restriction', 'time_restriction_display', 'created_at']
    list_filter = ['require_2fa', 'allow_without_2fa', 'enable_time_restriction']
    search_fields = ['group__name']
    
    fieldsets = (
        ('기본 정책', {
            'fields': ('group', 'require_2fa', 'allow_without_2fa', 'grace_period_hours')
        }),
        ('시간 제한 설정', {
            'fields': ('enable_time_restriction', 'allowed_start_time', 'allowed_end_time', 'allowed_weekdays', 'timezone'),
            'classes': ('collapse',)
        }),
    )
    
    def time_restriction_display(self, obj):
        """시간 제한 설정을 간단히 표시"""
        if not obj.enable_time_restriction:
            return "❌ 제한 없음"
        
        time_info = ""
        if obj.allowed_start_time and obj.allowed_end_time:
            time_info = f"{obj.allowed_start_time.strftime('%H:%M')} ~ {obj.allowed_end_time.strftime('%H:%M')}"
        
        weekdays = obj.get_allowed_weekdays_display()
        
        return f"✅ {time_info} ({weekdays})"
    
    time_restriction_display.short_description = "시간 제한"

# 기본 User Admin을 커스터마이징
class CustomUserAdmin(UserAdmin):
    def get_list_display(self, request):
        return super().get_list_display(request) + ('password_status', 'user_groups')
    
    def password_status(self, obj):
        if not obj.has_usable_password():
            return "🚫 VPN 전용 (Django 로그인 불가)"
        elif obj.is_superuser:
            return "👑 관리자"
        else:
            return "✅ Django 로그인 가능"
    password_status.short_description = "패스워드 상태"
    
    def user_groups(self, obj):
        groups = obj.groups.all()
        return ", ".join([group.name for group in groups]) if groups else "그룹 없음"
    user_groups.short_description = "소속 그룹"
    
    def get_fieldsets(self, request, obj=None):
        """사용자 편집 시 fieldset 커스터마이징"""
        fieldsets = super().get_fieldsets(request, obj)
        
        # VPN 전용 사용자 (패스워드 사용 불가)인 경우
        if obj and not obj.has_usable_password() and not obj.is_superuser:
            # 패스워드 필드를 제거한 새로운 fieldset 생성
            new_fieldsets = []
            for name, field_options in fieldsets:
                if name != 'Authentication and Authorization':
                    new_fieldsets.append((name, field_options))
                else:
                    # 패스워드 필드를 제외하고 나머지만 포함
                    fields = list(field_options.get('fields', ()))
                    if 'password' in fields:
                        fields.remove('password')
                    new_fieldsets.append((name, {**field_options, 'fields': tuple(fields)}))
            
            # VPN 전용 사용자임을 알리는 필드셋 추가
            new_fieldsets.insert(1, (
                'VPN 계정 정보', {
                    'fields': (),
                    'description': '🚫 이 계정은 VPN 전용입니다. Django Admin 로그인이 불가능하며, Directory Service에서 인증을 처리합니다.'
                }
            ))
            return new_fieldsets
        
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        """VPN 전용 사용자의 경우 일부 필드를 읽기 전용으로 만듦"""
        readonly_fields = super().get_readonly_fields(request, obj)
        
        if obj and not obj.has_usable_password() and not obj.is_superuser:
            # VPN 전용 사용자는 username을 변경할 수 없음 (Directory Service와 일치해야 함)
            return readonly_fields + ('username',)
        
        return readonly_fields

# 기본 User Admin을 새로운 것으로 교체
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
