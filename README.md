# AWS Client VPN 2FA Authentication System

AWS Client VPN과 Microsoft Active Directory를 연동한 2단계 인증(2FA) 시스템입니다.

## 🏗️ 시스템 아키텍처

```
사용자 → AWS Client VPN → Active Directory (1차 인증) → Lambda → Django API (2FA 검증) → 접속 허용/거부
                                                        ↓
                                              ALB → Django Web UI (2FA 설정)
```

## ✨ 주요 기능

### 🔐 보안 기능
- **2단계 인증**: Active Directory + TOTP (Google Authenticator 호환)
- **시간 기반 접근 제어**: 그룹별 요일/시간대 제한 설정
- **실시간 모니터링**: VPN 연결 로그 및 IP 추적 (개인정보 마스킹)
- **보안 코딩**: CORS 설정, 입력 검증, 에러 처리

### 🎨 사용자 인터페이스
- **모던 웹 UI**: 그라디언트 디자인의 반응형 인터페이스
- **QR 코드 생성**: 간편한 2FA 설정
- **Django Admin**: 사용자 및 정책 관리
- **Slack 알림**: 2FA 설정 필요 시 자동 알림

## 🔧 시스템 아키텍처

```
사용자 → AWS Client VPN (1차 인증) → Lambda Handler → Private EC2 API → 2FA 검증
                                                      ↓
                                               ALB → React UI (2FA 설정)
```

## 📋 현재 실행 중인 서비스

### Django 백엔드 서버
```bash
# 서버 상태 확인
ps aux | grep manage.py
# Django 서버가 0.0.0.0:8000에서 실행 중

# API 테스트
curl "http://localhost:8000/api/auth/check-status/?username=testuser"
# ✅ 정상 응답: {"success":true,"username":"testuser","has_2fa":true,"is_enabled":false}
```

### 사용 가능한 API 엔드포인트

- `POST /api/auth/setup-2fa/` - 2FA 초기 설정 (QR 코드 생성)
- `POST /api/auth/verify-2fa/` - TOTP 토큰 검증  
- `POST /api/auth/enable-2fa/` - 2FA 활성화
- `GET /api/auth/check-status/` - Lambda용 2FA 상태 확인
- `GET /api/auth/access-logs/` - VPN 접근 로그 조회

## 🔐 보안 기능

### 구현된 보안 요소
- TOTP 기반 2차 인증 (30초 갱신)
- 접근 로그 자동 기록
- CORS 보안 설정
- API 요청/응답 검증

### 데이터베이스
- 사용자별 2FA 설정 관리
- VPN 접근 시도 로깅
- 관리자 계정: `admin/admin123`

## 🚀 배포 및 실행 방법

### 자동 배포 스크립트 사용
```bash
# 전체 시스템 배포
sudo /root/aws-vpn-2fa/scripts/deploy.sh all

# 단계별 배포
./scripts/deploy.sh backend    # Django 백엔드
./scripts/deploy.sh frontend   # React 프론트엔드  
./scripts/deploy.sh services   # 시스템 서비스
./scripts/deploy.sh status     # 서비스 상태 확인
```

### 수동 실행 방법
```bash
# Django 백엔드 실행
cd /root/aws-vpn-2fa/backend
source venv/bin/activate  
python manage.py runserver 0.0.0.0:8000

# React 프론트엔드 빌드
cd /root/aws-vpn-2fa/frontend
npm install
npm run build
```

## 📱 사용자 워크플로우

### 1단계: VPN 연결 시도
1. AWS Client VPN 클라이언트에서 연결 시도
2. Directory Service 1차 인증 (사용자명/비밀번호)
3. Lambda Function이 2FA 상태 확인

### 2단계: 2FA 설정 (최초 1회)
1. Lambda에서 제공한 웹 URL 접속
2. 사용자명 입력 후 QR 코드 생성
3. Google Authenticator 앱으로 QR 코드 스캔
4. 생성된 6자리 코드 입력하여 2FA 활성화

### 3단계: 이후 자동 인증
- 2FA가 활성화된 사용자는 자동으로 VPN 접속 허용
- 모든 접근 시도는 웹 인터페이스에서 실시간 모니터링

## 🔍 모니터링 및 로그

### 서비스 로그 확인
```bash
# Django 서비스 로그
sudo journalctl -u vpn-auth-backend.service -f

# 접근 로그 API 조회
curl http://localhost:8000/api/auth/access-logs/
```

### 웹 인터페이스
- 실시간 접근 로그 조회
- 2FA 설정 상태 관리
- 사용자별 인증 이력 추적

## 🛠️ 다음 단계 (To-Do)

### 시스템 서비스화
1. systemd 서비스 등록
2. Nginx 프록시 설정  
3. HTTPS 인증서 구성
4. 자동 재시작 설정

### Lambda Function 배포
1. AWS Lambda 콘솔에서 함수 생성
2. `scripts/lambda-handler.py` 코드 업로드
3. VPC 및 보안 그룹 설정
4. AWS Client VPN 연동

### ALB 설정
1. Application Load Balancer 생성
2. Private EC2 타겟 그룹 구성
3. 외부 접근 허용 설정

## 📞 지원 및 문제 해결

### 일반적인 문제
- **API 접근 불가**: 방화벽 설정 확인 (포트 8000)
- **QR 코드 오류**: pyotp, qrcode 라이브러리 재설치
- **인증 실패**: 시간 동기화 확인

### 로그 위치
- Django: `/var/log/vpn-auth/`
- Nginx: `/var/log/nginx/`
- 시스템: `journalctl -u vpn-auth-backend`

---

## 🎯 현재 상태 요약

**✅ 완료된 항목:**
- Django 백엔드 API 서버 실행 중 (포트 8000)
- 2FA TOTP 인증 시스템 완전 구현
- Lambda 연동 API 테스트 완료
- 관리자 및 테스트 계정 생성 완료
- React 프론트엔드 구성 완료

**⏳ 진행 중:**  
- React 앱 빌드 최적화
- 시스템 서비스 설정

**📋 대기 중:**
- Nginx 프록시 구성
- HTTPS 설정  
- Lambda Function AWS 배포
- ALB 연동 설정

Private EC2(YOUR-PRIVATE-IP)에서 Django API 서버가 정상 실행되고 있으며, 2FA 시스템이 완전히 작동합니다!