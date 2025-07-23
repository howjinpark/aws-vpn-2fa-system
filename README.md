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

## 🚀 빠른 시작

### 환경 요구사항
- Python 3.8+
- Node.js 16+
- AWS CLI 구성
- Django 5.x
- React 18+

### 설치 및 실행

```bash
# 저장소 클론
git clone https://github.com/howjinpark/aws-vpn-2fa-system.git
cd aws-vpn-2fa-system

# 백엔드 설정
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 변경

# 데이터베이스 마이그레이션
python manage.py migrate
python manage.py createsuperuser

# Django 서버 실행
python manage.py runserver 0.0.0.0:8000

# 프론트엔드 설정 (새 터미널)
cd frontend
npm install
npm run build
```

## 📡 API 엔드포인트

- `POST /api/auth/setup-2fa/` - 2FA 초기 설정 (QR 코드 생성)
- `POST /api/auth/verify-2fa/` - TOTP 토큰 검증  
- `POST /api/auth/enable-2fa/` - 2FA 활성화
- `GET /api/auth/check-status/` - Lambda용 2FA 상태 확인
- `GET /api/auth/access-logs/` - VPN 접근 로그 조회
- `GET /api/auth/health/` - 헬스체크 엔드포인트

## 📱 사용자 워크플로우

### 1️⃣ VPN 연결 시도
1. AWS Client VPN 클라이언트에서 연결 시도
2. Directory Service 1차 인증 (사용자명/비밀번호)
3. Lambda Function이 2FA 상태 확인

### 2️⃣ 2FA 설정 (최초 1회)
1. Lambda에서 제공한 웹 URL 접속
2. 사용자명 입력 후 QR 코드 생성
3. Google Authenticator 앱으로 QR 코드 스캔
4. 생성된 6자리 코드 입력하여 2FA 활성화

### 3️⃣ 자동 인증
- 2FA가 활성화된 사용자는 자동으로 VPN 접속 허용
- 모든 접근 시도는 웹 인터페이스에서 실시간 모니터링

## 🛠️ AWS 인프라 설정

### Lambda Function 배포
1. AWS Lambda 콘솔에서 함수 생성 (`AWSClientVPN-` 접두사 필수)
2. `lambda/lambda_function.py` 코드 업로드
3. 환경변수 설정 (`lambda/environment.json` 참고)
4. VPC 및 보안 그룹 설정

### Application Load Balancer
1. ALB 생성 및 타겟 그룹 구성
2. 헬스체크 경로: `/api/auth/health/`
3. Private EC2 인스턴스 연결

### Client VPN 설정
1. AWS Client VPN 엔드포인트 생성
2. Active Directory 연동 설정
3. Lambda 함수를 Pre-Authentication Handler로 등록

## 🔍 모니터링

### 로그 확인
```bash
# Django 애플리케이션 로그
tail -f logs/django.log

# 접근 로그 API 조회
curl "http://localhost:8000/api/auth/access-logs/"

# VPN 연결 동기화 (cron 작업)
python manage.py sync_vpn_connections --dry-run
```

### 웹 인터페이스
- **Django Admin**: `/admin/` (관리자 계정으로 로그인)
- **2FA 설정**: `/` (메인 페이지)
- **API 문서**: `/api/` (DRF 브라우저블 API)

## 🛡️ 보안 고려사항

### 환경변수 관리
모든 민감한 정보는 환경변수로 관리:
```env
DJANGO_SECRET_KEY=your-secret-key
SLACK_WEBHOOK_URL=your-webhook-url
AWS_REGION=your-region
CLIENT_VPN_ENDPOINT_ID=your-endpoint-id
ALB_DOMAIN=your-alb-domain
```

### 데이터 보호
- TOTP 시크릿 키 암호화 저장
- VPN IP 주소 마스킹 처리
- 접근 로그 개인정보 보호
- CORS 및 CSRF 보호 설정

## 📞 문제 해결

### 일반적인 오류
- **500 Error**: 환경변수 설정 확인
- **API 접근 불가**: 방화벽 설정 확인 (포트 8000)
- **QR 코드 오류**: pyotp, qrcode 라이브러리 재설치
- **Lambda Timeout**: VPC 내 DNS 설정 확인

### 디버깅
```bash
# Django 디버그 모드 활성화
export DJANGO_DEBUG=True

# 상세 로그 확인
python manage.py runserver --verbosity=2

# 데이터베이스 상태 확인
python manage.py dbshell
```

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📧 연락처

프로젝트 관련 문의: [GitHub Issues](https://github.com/howjinpark/aws-vpn-2fa-system/issues)

---

⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!