import json
import urllib3
import os
from typing import Dict, Any

# Private EC2 백엔드 API 엔드포인트
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://YOUR-PRIVATE-IP:8000/api/auth')
WEB_REDIRECT_URL = os.environ.get('WEB_REDIRECT_URL', 'http://your-alb-domain.elb.amazonaws.com')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Client VPN Pre-Authentication Handler
    VPN 연결 시도 시 2FA 상태를 확인하고 필요에 따라 웹 리다이렉션을 수행
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    # 요청 파라미터 추출
    username = event.get('username')
    client_ip = event.get('public-ip', event.get('client-ip', event.get('client_ip', '')))
    connection_id = event.get('connection-id', '')
    groups = event.get('groups', [])  # Directory Service 그룹 정보
    
    print(f"User: {username}, Groups: {groups}, Client-IP: {client_ip}")
    
    return handle_pre_authentication(username, client_ip, connection_id, groups)

def handle_pre_authentication(username: str, client_ip: str, connection_id: str, groups: list) -> Dict[str, Any]:
    """VPN 연결 전 2FA 상태 확인"""
    print(f"Pre-authentication for {username}")
    
    if not username:
        print("Username not provided in event")
        return {
            'allow': False,
            'posture-compliance-statuses': ['missing-username'],
            'schema-version': 'v3',
            'error-msg-on-failed-posture-compliance': '사용자명이 제공되지 않았습니다.'
        }
    
    print(f"Processing pre-authentication for user: {username}, IP: {client_ip}")
    
    try:
        # Private EC2 백엔드 API로 2FA 상태 확인
        http = urllib3.PoolManager()
        
        # 2FA 상태 확인 API 호출
        check_url = f"{BACKEND_API_URL}/check-status/"
        params = {
            'username': username,
            'client_ip': client_ip,
            'connection_id': connection_id,
            'source': 'lambda_vpn_check'
        }
        
        print(f"Calling API: {check_url} with params: {params}")
        
        response = http.request('GET', check_url, fields=params, timeout=10)
        
        if response.status != 200:
            print(f"Backend API error: {response.status}, Response: {response.data}")
            return {
                'allow': False,
                'posture-compliance-statuses': ['api-error'],
                'schema-version': 'v3',
                'error-msg-on-failed-posture-compliance': f'인증 서버와 통신할 수 없습니다. (Status: {response.status})'
            }
        
        data = json.loads(response.data.decode('utf-8'))
        print(f"API Response: {data}")
        
        # 응답 데이터 확인
        if not data.get('success'):
            print(f"API response error: {data}")
            
            # 시간 제한 에러인 경우
            if data.get('error_code') == 'TIME_RESTRICTION':
                return {
                    'allow': False,
                    'posture-compliance-statuses': ['time-restriction'],
                    'schema-version': 'v3',
                    'error-msg-on-failed-posture-compliance': data.get('error', '시간 제한으로 접근이 거부되었습니다.')
                }
            
            return {
                'allow': False,
                'posture-compliance-statuses': ['api-response-error'],
                'schema-version': 'v3',
                'error-msg-on-failed-posture-compliance': '인증 상태를 확인할 수 없습니다.'
            }
        
        # 2FA가 설정되어 있고 활성화된 경우 VPN 접속 허용
        if data.get('has_2fa') and data.get('is_enabled'):
            print(f"2FA verified for user: {username} - ACCESS GRANTED")
            result = {
                'allow': True,
                'error-msg-on-denied-connection': '',
                'posture-compliance-statuses': [],
                'schema-version': 'v3'
            }
            print(f"Returning result: {result}")
            return result
        
        # 2FA가 설정되지 않았거나 비활성화된 경우
        if data.get('requires_setup') or not data.get('is_enabled'):
            # 웹 페이지로 리다이렉션하여 2FA 설정 요청
            redirect_url = f"{WEB_REDIRECT_URL}?username={username}&action=setup_2fa"
            
            print(f"2FA setup required for user: {username} - ACCESS DENIED")
            print(f"Redirect URL: {redirect_url}")
            
            return {
                'allow': False,
                'posture-compliance-statuses': ['requires-2fa-setup'],
                'schema-version': 'v3',
                'error-msg-on-failed-posture-compliance': f'【2차 인증 필요】 웹브라우저에서 {WEB_REDIRECT_URL} 접속 → 사용자명: {username} 입력 → 2FA 설정 완료 후 VPN 재연결하세요'
            }
        
        # 기본적으로 접속 거부
        print(f"Default deny for user: {username}")
        return {
            'allow': False,
            'posture-compliance-statuses': ['2fa-required'],
            'schema-version': 'v3',
            'error-msg-on-failed-posture-compliance': f'【2차 인증 필요】 웹브라우저에서 {WEB_REDIRECT_URL} 접속하여 2FA 설정 후 VPN을 다시 연결하세요'
        }
        
    except urllib3.exceptions.TimeoutError:
        print(f"Timeout connecting to backend API for user: {username}")
        return {
            'allow': False,
            'posture-compliance-statuses': ['server-timeout'],
            'schema-version': 'v3',
            'error-msg-on-failed-posture-compliance': '인증 서버 연결 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.'
        }
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {
            'allow': False,
            'posture-compliance-statuses': ['json-error'],
            'schema-version': 'v3',
            'error-msg-on-failed-posture-compliance': '인증 서버 응답을 처리할 수 없습니다.'
        }
    
    except Exception as e:
        print(f"Unexpected error in lambda_handler: {str(e)}")
        return {
            'allow': False,
            'posture-compliance-statuses': ['unexpected-error'],
            'schema-version': 'v3',
            'error-msg-on-failed-posture-compliance': '인증 처리 중 예상치 못한 오류가 발생했습니다.'
        }