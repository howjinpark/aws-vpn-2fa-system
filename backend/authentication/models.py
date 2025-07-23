from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
import pyotp
import qrcode
import io
import base64
from datetime import timedelta, datetime, time
import uuid
import pytz

class VPNGroupPolicy(models.Model):
    """그룹별 VPN 2FA 정책"""
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='vpn_policy')
    require_2fa = models.BooleanField(default=True, help_text="이 그룹은 2FA를 필수로 요구합니다")
    allow_without_2fa = models.BooleanField(default=False, help_text="2FA 없이도 VPN 접근 허용")
    grace_period_hours = models.IntegerField(default=24, help_text="2FA 설정 유예 기간 (시간)")
    
    # 시간 제한 설정
    enable_time_restriction = models.BooleanField(default=False, help_text="시간 제한 활성화")
    allowed_start_time = models.TimeField(null=True, blank=True, help_text="접속 허용 시작 시간 (예: 09:00)")
    allowed_end_time = models.TimeField(null=True, blank=True, help_text="접속 허용 종료 시간 (예: 18:00)")
    allowed_weekdays = models.CharField(
        max_length=20, 
        default="1,2,3,4,5", 
        help_text="접속 허용 요일 (월=1, 화=2, 수=3, 목=4, 금=5, 토=6, 일=7)"
    )
    timezone = models.CharField(max_length=50, default="Asia/Seoul", help_text="시간대 설정")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "VPN Group Policy"
        verbose_name_plural = "VPN Group Policies"
    
    def __str__(self):
        return f"{self.group.name} - {'2FA Required' if self.require_2fa else '2FA Optional'}"
    
    def is_access_allowed_now(self):
        """현재 시간에 접속이 허용되는지 확인"""
        if not self.enable_time_restriction:
            return True, "시간 제한 없음"
        
        # 설정된 시간대로 현재 시간 가져오기
        try:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
        except:
            # 잘못된 시간대인 경우 서울 시간 사용
            tz = pytz.timezone('Asia/Seoul')
            now = datetime.now(tz)
        
        current_weekday = now.isoweekday()  # 월=1, 일=7
        current_time = now.time()
        
        # 허용 요일 체크
        allowed_days = [int(d.strip()) for d in self.allowed_weekdays.split(',') if d.strip()]
        if current_weekday not in allowed_days:
            weekday_names = {1: '월', 2: '화', 3: '수', 4: '목', 5: '금', 6: '토', 7: '일'}
            current_day_name = weekday_names.get(current_weekday, str(current_weekday))
            return False, f"허용되지 않은 요일입니다 (현재: {current_day_name}요일)"
        
        # 허용 시간 체크
        if self.allowed_start_time and self.allowed_end_time:
            if self.allowed_start_time <= self.allowed_end_time:
                # 같은 날 내의 시간 범위 (예: 09:00 ~ 18:00)
                if not (self.allowed_start_time <= current_time <= self.allowed_end_time):
                    return False, f"허용된 시간이 아닙니다 (허용시간: {self.allowed_start_time} ~ {self.allowed_end_time})"
            else:
                # 날짜를 넘나드는 시간 범위 (예: 22:00 ~ 06:00)
                if not (current_time >= self.allowed_start_time or current_time <= self.allowed_end_time):
                    return False, f"허용된 시간이 아닙니다 (허용시간: {self.allowed_start_time} ~ {self.allowed_end_time})"
        
        return True, f"접속 허용 (현재: {current_time.strftime('%H:%M')})"
    
    def get_allowed_weekdays_display(self):
        """허용 요일을 한글로 표시"""
        weekday_names = {1: '월', 2: '화', 3: '수', 4: '목', 5: '금', 6: '토', 7: '일'}
        try:
            days = [int(d.strip()) for d in self.allowed_weekdays.split(',') if d.strip()]
            return ', '.join([weekday_names.get(d, str(d)) + '요일' for d in sorted(days)])
        except:
            return self.allowed_weekdays

class UserTwoFactorAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor_auth')
    secret_key = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_tokens = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - 2FA {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def generate_secret_key(self):
        """2FA 비밀 키 생성"""
        self.secret_key = pyotp.random_base32()
        self.save()
        return self.secret_key
    
    def get_qr_code(self):
        """QR 코드 생성"""
        if not self.secret_key:
            self.generate_secret_key()
        
        totp_uri = pyotp.totp.TOTP(self.secret_key).provisioning_uri(
            name=self.user.username,
            issuer_name="AWS VPN 2FA"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_token(self, token):
        """TOTP 토큰 검증"""
        if not self.secret_key:
            return False
        
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)

class VPNAccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=150)
    client_ip = models.GenericIPAddressField()
    access_time = models.DateTimeField(auto_now_add=True)
    two_factor_verified = models.BooleanField(default=False)
    access_granted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-access_time']
    
    def __str__(self):
        return f"{self.username} - {self.client_ip} - {'Granted' if self.access_granted else 'Denied'}"
