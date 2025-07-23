import boto3
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from authentication.models import UserTwoFactorAuth, VPNAccessLog
from django.utils import timezone
import os

class Command(BaseCommand):
    help = 'AWS API를 통해 활성 VPN 연결을 조회하고 로그에 기록'
    
    def mask_username(self, username):
        """사용자명 마스킹 처리"""
        if '@' in username:
            local, domain = username.split('@', 1)
            if len(local) > 2:
                masked_local = local[:2] + '*' * (len(local) - 2)
            else:
                masked_local = local[0] + '*'
            return f"{masked_local}@{domain}"
        else:
            if len(username) > 2:
                return username[:2] + '*' * (len(username) - 2)
            else:
                return username[0] + '*'
    
    def mask_ip(self, ip):
        """IP 주소 마스킹 처리"""
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
        return "xxx.xxx.xxx.xxx"

    def add_arguments(self, parser):
        parser.add_argument(
            '--endpoint-id',
            type=str,
            default=os.getenv('CLIENT_VPN_ENDPOINT_ID', 'cvpn-endpoint-xxxxxx'),
            help='Client VPN Endpoint ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 로그 기록 없이 테스트 실행'
        )

    def handle(self, *args, **options):
        endpoint_id = options['endpoint_id']
        dry_run = options['dry_run']
        
        self.stdout.write(f"🔍 Client VPN 연결 조회 중... (Endpoint: {endpoint_id})")
        
        try:
            # AWS EC2 클라이언트 생성
            region = os.getenv('AWS_REGION', 'your-aws-region')
            ec2_client = boto3.client('ec2', region_name=region)
            
            # 활성 VPN 연결 조회
            response = ec2_client.describe_client_vpn_connections(
                ClientVpnEndpointId=endpoint_id
            )
            
            connections = response.get('Connections', [])
            active_connections = [conn for conn in connections if conn['Status']['Code'] == 'active']
            
            self.stdout.write(f"📊 총 연결: {len(connections)}, 활성 연결: {len(active_connections)}")
            
            logged_count = 0
            
            for conn in active_connections:
                username = conn.get('Username')
                vpn_ip = conn.get('ClientIp')
                connection_id = conn.get('ConnectionId')
                established_time = conn.get('ConnectionEstablishedTime')
                
                if not username or not vpn_ip:
                    continue
                
                # 개인정보 마스킹 처리
                masked_username = self.mask_username(username)
                masked_ip = self.mask_ip(vpn_ip)
                self.stdout.write(f"🔗 활성 연결: {masked_username} -> {masked_ip} (연결시간: {established_time})")
                
                if dry_run:
                    self.stdout.write(f"   [DRY-RUN] 로그 기록 시뮬레이션")
                    logged_count += 1
                    continue
                
                try:
                    # 사용자 및 2FA 정보 조회
                    user = User.objects.get(username=username)
                    two_factor_auth = UserTwoFactorAuth.objects.get(user=user)
                    
                    # 중복 로그 방지: 같은 connection_id가 이미 기록되었는지 확인
                    existing_log = VPNAccessLog.objects.filter(
                        username=username,
                        client_ip=vpn_ip,
                        access_time__gte=timezone.now() - timezone.timedelta(hours=1)
                    ).first()
                    
                    if existing_log:
                        self.stdout.write(f"   ⚠️  중복 로그 건너뜀: {masked_username} -> {masked_ip}")
                        continue
                    
                    # VPN 연결 로그 기록
                    VPNAccessLog.objects.create(
                        user=user,
                        username=username,
                        client_ip=vpn_ip,
                        two_factor_verified=two_factor_auth.is_enabled,
                        access_granted=True  # 활성 연결이므로 접근 허용됨
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"   ✅ 로그 기록 완료: {masked_username} -> {masked_ip}")
                    )
                    logged_count += 1
                    
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  사용자를 찾을 수 없음: {masked_username}")
                    )
                except UserTwoFactorAuth.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  2FA 정보를 찾을 수 없음: {masked_username}")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ 로그 기록 실패: {masked_username} -> {str(e)}")
                    )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"🧪 DRY-RUN 완료: {logged_count}개 연결이 로그에 기록될 예정")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"🎉 동기화 완료: {logged_count}개 VPN 연결이 로그에 기록됨")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ AWS API 호출 실패: {str(e)}")
            )
            return