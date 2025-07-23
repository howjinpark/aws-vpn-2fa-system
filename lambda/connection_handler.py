import json
import urllib3
import os
from typing import Dict, Any

# Private EC2 백엔드 API 엔드포인트
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://YOUR-PRIVATE-IP:8000/api/auth')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Client VPN Connection Handler
    VPN 연결 성공 후 실제 VPN IP와 함께 접근 로그 기록
    """
    
    print(f"Connection event: {json.dumps(event)}")
    
    # 연결 정보 추출
    username = event.get('username')
    vpn_ip = event.get('vpn-ip', '')  # 실제 VPN IP
    connection_id = event.get('connection-id', '')
    public_ip = event.get('public-ip', '')
    
    print(f"VPN Connection: User={username}, VPN-IP={vpn_ip}, Public-IP={public_ip}")
    
    if not username or not vpn_ip:
        print("Missing username or VPN IP")
        return {'allow': True}
    
    try:
        # Private EC2 백엔드 API로 VPN 접근 로그 기록
        http = urllib3.PoolManager()
        
        log_url = f"{BACKEND_API_URL}/log-vpn-connection/"
        data = {
            'username': username,
            'vpn_ip': vpn_ip,
            'public_ip': public_ip,
            'connection_id': connection_id,
            'connection_status': 'connected'
        }
        
        print(f"Logging VPN connection: {data}")
        
        response = http.request('POST', log_url, 
                              body=json.dumps(data),
                              headers={'Content-Type': 'application/json'},
                              timeout=10)
        
        if response.status == 200:
            print(f"VPN connection logged successfully for {username}")
        else:
            print(f"Failed to log VPN connection: {response.status}")
            
    except Exception as e:
        print(f"Error logging VPN connection: {str(e)}")
    
    # Connection Handler는 항상 allow=True 반환
    return {'allow': True}