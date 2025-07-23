from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import requests
from .models import UserTwoFactorAuth, VPNAccessLog
import json
import os

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def setup_2fa(request):
    """2FA 설정 API"""
    try:
        # DRF에서는 request.data를 사용
        username = request.data.get('username')
        
        user = User.objects.get(username=username)
        two_factor_auth, created = UserTwoFactorAuth.objects.get_or_create(user=user)
        
        if not two_factor_auth.secret_key:
            two_factor_auth.generate_secret_key()
        
        qr_code = two_factor_auth.get_qr_code()
        
        return Response({
            'success': True,
            'qr_code': qr_code,
            'secret_key': two_factor_auth.secret_key,
            'is_enabled': two_factor_auth.is_enabled
        })
        
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)

@csrf_exempt  
def verify_2fa(request):
    """2FA 토큰 검증 API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        username = data.get('username')
        token = data.get('token')
        client_ip = data.get('client_ip', request.META.get('REMOTE_ADDR'))
        
        user = User.objects.get(username=username)
        two_factor_auth = UserTwoFactorAuth.objects.get(user=user)
        
        is_valid = two_factor_auth.verify_token(token)
        
        # 첫 번째 인증 성공 시 2FA 활성화
        if is_valid and not two_factor_auth.is_enabled:
            two_factor_auth.is_enabled = True
            two_factor_auth.save()
        
        # 접근 로그 기록
        VPNAccessLog.objects.create(
            user=user,
            username=username,
            client_ip=client_ip,
            two_factor_verified=is_valid,
            access_granted=is_valid
        )
        
        if is_valid:
            return JsonResponse({
                'success': True,
                'access_granted': True,
                'message': '2FA 인증 성공'
            })
        else:
            return JsonResponse({
                'success': False,
                'access_granted': False,
                'message': '2FA 인증 실패'
            })
            
    except (User.DoesNotExist, UserTwoFactorAuth.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'User or 2FA not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
def enable_2fa(request):
    """2FA 활성화 API"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        token = data.get('token')
        
        user = User.objects.get(username=username)
        two_factor_auth = UserTwoFactorAuth.objects.get(user=user)
        
        if two_factor_auth.verify_token(token):
            two_factor_auth.is_enabled = True
            two_factor_auth.save()
            
            return Response({
                'success': True,
                'message': '2FA가 활성화되었습니다.'
            })
        else:
            return Response({
                'success': False,
                'message': '잘못된 토큰입니다.'
            }, status=400)
            
    except (User.DoesNotExist, UserTwoFactorAuth.DoesNotExist):
        return Response({'success': False, 'error': 'User or 2FA not found'}, status=404)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)

def send_2fa_setup_slack(user):
    """2FA 설정 필요 슬랙 메시지 발송"""
    slack_webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
    if not slack_webhook_url:
        print("SLACK_WEBHOOK_URL not configured")
        return False
    
    alb_domain = os.getenv('ALB_DOMAIN', 'localhost')
    setup_url = f'http://{alb_domain}?username={user.username}&action=setup_2fa'
    
    message = {
        "text": f"🚨 VPN 2FA 설정 필요 알림",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔐 AWS VPN 2차 인증 설정 필요"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*사용자:* `{user.username}`\n*상태:* VPN 연결 시도 감지, 2FA 미설정으로 접속 차단"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"VPN 접속을 위해 아래 링크에서 2FA를 설정해주세요:"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "2FA 설정하기"
                        },
                        "url": setup_url,
                        "style": "primary"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏰ {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(slack_webhook_url, json=message, timeout=10)
        if response.status_code == 200:
            print(f"Slack message sent for user: {user.username}")
            return True
        else:
            print(f"Slack message failed: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Slack send failed for {user.username}: {str(e)}")
        return False

@api_view(['GET'])
@permission_classes([AllowAny])
def check_2fa_status(request):
    """Lambda에서 호출하는 2FA 상태 확인 API"""
    username = request.GET.get('username')
    groups_param = request.GET.get('groups', '')
    groups = [g.strip() for g in groups_param.split(',') if g.strip()] if groups_param else []
    send_email = request.GET.get('send_email', 'true').lower() == 'true'  # 이메일 발송 여부
    client_ip = request.GET.get('client_ip', request.META.get('REMOTE_ADDR', ''))
    connection_id = request.GET.get('connection_id', '')
    source = request.GET.get('source', 'unknown')
    
    if not username:
        return Response({'success': False, 'error': 'Username required'}, status=400)
    
    try:
        user = User.objects.get(username=username)
        
        # 사용자 그룹별 시간 제한 체크
        user_groups = user.groups.all()
        for group in user_groups:
            try:
                policy = group.vpn_policy
                if policy.enable_time_restriction:
                    is_allowed, time_message = policy.is_access_allowed_now()
                    if not is_allowed:
                        print(f"Time restriction denied for {username}: {time_message}")
                        return Response({
                            'success': False,
                            'username': username,
                            'has_2fa': False,
                            'is_enabled': False,
                            'requires_setup': False,
                            'error': f'시간 제한으로 접근 거부: {time_message}',
                            'error_code': 'TIME_RESTRICTION'
                        })
                    else:
                        print(f"Time check passed for {username}: {time_message}")
            except Exception as e:
                print(f"Error checking time restriction for group {group.name}: {e}")
                continue
        
        two_factor_auth = UserTwoFactorAuth.objects.get(user=user)
        
        # Lambda에서 호출된 경우가 아닐 때만 VPN 접근 로그 기록
        if source != 'lambda_vpn_check':
            # VPN 접근 로그 기록
            VPNAccessLog.objects.create(
                user=user,
                username=username,
                client_ip=client_ip,
                two_factor_verified=two_factor_auth.is_enabled,
                access_granted=two_factor_auth.is_enabled
            )
            print(f"VPN access log recorded for {username} from {client_ip}")
        
        # 2FA가 비활성화된 경우 슬랙 메시지 발송
        if send_email and not two_factor_auth.is_enabled:
            slack_sent = send_2fa_setup_slack(user)
            print(f"2FA setup Slack message sent to {username}: {slack_sent}")
        
        return Response({
            'success': True,
            'username': username,
            'has_2fa': True,
            'is_enabled': two_factor_auth.is_enabled,
            'requires_setup': not two_factor_auth.secret_key
        })
        
    except User.DoesNotExist:
        # 사용자가 없는 경우에도 이메일 발송 시도 (이메일이 있다면)
        if send_email:
            print(f"User {username} does not exist in Django, cannot send email")
        
        return Response({
            'success': True,
            'username': username,
            'has_2fa': False,
            'is_enabled': False,
            'requires_setup': True
        })
    except UserTwoFactorAuth.DoesNotExist:
        try:
            user = User.objects.get(username=username)
            # 2FA 레코드가 없는 경우 슬랙 메시지 발송
            if send_email:
                slack_sent = send_2fa_setup_slack(user)
                print(f"2FA setup Slack message sent to {username}: {slack_sent}")
        except User.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'username': username,
            'has_2fa': False,
            'is_enabled': False,
            'requires_setup': True
        })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)

@ensure_csrf_cookie
def setup_2fa_web(request):
    """2FA 설정 웹 페이지"""
    username = request.GET.get('username', '')
    action = request.GET.get('action', '')
    
    # username이 없으면 입력 폼 표시
    if not username:
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AWS VPN 2FA - 사용자 입력</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       min-height: 100vh; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 100px auto; 
                             background: white; border-radius: 10px; 
                             box-shadow: 0 15px 35px rgba(0,0,0,0.1); padding: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #333; margin-bottom: 10px; }}
                .header p {{ color: #666; }}
                .form-group {{ margin: 20px 0; }}
                .form-group label {{ display: block; margin-bottom: 8px; 
                                    color: #333; font-weight: 500; }}
                .form-group input {{ width: 100%; padding: 12px; border: 2px solid #e1e5e9;
                                    border-radius: 6px; font-size: 16px; box-sizing: border-box; }}
                .form-group input:focus {{ outline: none; border-color: #667eea; }}
                .btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       color: white; padding: 12px 30px; border: none; border-radius: 6px;
                       font-size: 16px; cursor: pointer; width: 100%; margin-top: 20px; }}
                .btn:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
                .info {{ background: #f8f9fa; padding: 15px; border-radius: 6px; 
                        border-left: 4px solid #667eea; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 AWS VPN 2FA 설정</h1>
                    <p>VPN 접속을 위한 2단계 인증을 설정합니다</p>
                </div>
                
                <form method="GET">
                    <div class="form-group">
                        <label for="username">사용자명 (Active Directory)</label>
                        <input type="text" id="username" name="username" 
                               placeholder="예: username@your-domain.com" required>
                    </div>
                    
                    <button type="submit" class="btn">2FA 설정 시작</button>
                </form>
                
                <div class="info">
                    <strong>참고:</strong> Active Directory에 등록된 전체 사용자명을 입력하세요.
                    (예: username@your-domain.com)
                </div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)
    
    # 간단한 HTML 페이지 반환
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="csrf-token" content="{request.META.get('CSRF_COOKIE', '')}">
        <title>AWS VPN 2FA 설정</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .header {{ text-align: center; color: #333; }}
            .step {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .button {{ background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .qr-container {{ text-align: center; margin: 20px 0; }}
            #qrcode {{ margin: 20px auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 AWS VPN 2차 인증(2FA) 설정</h1>
            <p>사용자: <strong>{username}</strong></p>
        </div>
        
        <div class="step">
            <h3>1단계: QR 코드 생성</h3>
            <p>먼저 2FA 비밀키를 생성해야 합니다.</p>
            <button class="button" onclick="generateQR()">QR 코드 생성</button>
        </div>
        
        <div class="step" id="qr-step" style="display:none;">
            <h3>2단계: Google Authenticator 설정</h3>
            <div class="qr-container">
                <div id="qrcode"></div>
                <p>Google Authenticator 앱으로 위 QR 코드를 스캔하세요.</p>
            </div>
        </div>
        
        <div class="step" id="verify-step" style="display:none;">
            <h3>3단계: 인증번호 확인</h3>
            <p>Google Authenticator에서 생성된 6자리 인증번호를 입력하세요:</p>
            <input type="text" id="token" placeholder="123456" maxlength="6" style="padding: 10px; font-size: 18px; width: 150px;">
            <button class="button" onclick="verifyToken()">인증 완료</button>
        </div>
        
        <div class="step" id="success-step" style="display:none;">
            <h3>✅ 설정 완료!</h3>
            <p>2FA 설정이 완료되었습니다. 이제 VPN에 재연결해보세요.</p>
        </div>

        <script>
            function getCookie(name) {{
                let cookieValue = null;
                if (document.cookie && document.cookie !== '') {{
                    const cookies = document.cookie.split(';');
                    for (let i = 0; i < cookies.length; i++) {{
                        const cookie = cookies[i].trim();
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }}
                    }}
                }}
                return cookieValue;
            }}
            
            function generateQR() {{
                const csrftoken = getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]').getAttribute('content');
                fetch('/api/auth/setup-2fa/', {{
                    method: 'POST',
                    headers: {{ 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    }},
                    body: JSON.stringify({{ username: '{username}' }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        document.getElementById('qrcode').innerHTML = '<img src="data:image/png;base64,' + data.qr_code + '" alt="QR Code">';
                        document.getElementById('qr-step').style.display = 'block';
                        document.getElementById('verify-step').style.display = 'block';
                    }} else {{
                        alert('QR 코드 생성 실패: ' + data.error);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('QR 코드 생성 실패: 네트워크 오류');
                }});
            }}
            
            function verifyToken() {{
                const token = document.getElementById('token').value;
                if (token.length !== 6) {{
                    alert('6자리 인증번호를 입력하세요.');
                    return;
                }}
                
                const csrftoken = getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]').getAttribute('content');
                fetch('/api/auth/verify-2fa/', {{
                    method: 'POST',
                    headers: {{ 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    }},
                    body: JSON.stringify({{ username: '{username}', token: token }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        document.getElementById('success-step').style.display = 'block';
                        document.getElementById('verify-step').style.display = 'none';
                    }} else {{
                        alert('인증 실패: ' + data.error);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('인증 실패: 네트워크 오류');
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """ALB 헬스체크용 엔드포인트"""
    return Response({
        'status': 'healthy',
        'service': 'vpn-2fa-backend',
        'timestamp': timezone.now().isoformat()
    })


@api_view(['GET'])
def access_logs(request):
    """VPN 접근 로그 조회 API"""
    try:
        logs = VPNAccessLog.objects.all()[:50]  # 최근 50개
        log_data = [
            {
                'username': log.username,
                'client_ip': log.client_ip,
                'access_time': log.access_time.isoformat(),
                'two_factor_verified': log.two_factor_verified,
                'access_granted': log.access_granted
            }
            for log in logs
        ]
        
        return Response({
            'success': True,
            'logs': log_data
        })
        
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)
