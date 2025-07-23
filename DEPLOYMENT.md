# 🚀 배포 가이드

## 📋 배포 전 준비사항

### 1. 환경변수 설정
```bash
cd backend
cp .env.example .env
```

`.env` 파일을 열어서 다음 값들을 실제 값으로 변경하세요:

```env
# Django 보안 설정
DJANGO_SECRET_KEY=실제-50자-이상의-랜덤-시크릿-키
DJANGO_DEBUG=False

# 외부 서비스 연동
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# AWS 설정
AWS_REGION=실제-AWS-리전
CLIENT_VPN_ENDPOINT_ID=실제-VPN-엔드포인트-ID

# 보안 설정  
ALB_DOMAIN=실제-ALB-도메인.elb.amazonaws.com
PRIVATE_IP=실제-프라이빗-IP
ALLOWED_HOSTS=실제-프라이빗-IP,실제-ALB-도메인,localhost,127.0.0.1
```

### 2. Django 설정
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 패키지 설치
pip install -r requirements.txt

# 데이터베이스 마이그레이션
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser

# Static 파일 수집
python manage.py collectstatic
```

### 3. Lambda 함수 배포
1. AWS Lambda 콘솔에서 새 함수 생성
2. 함수 이름: `AWSClientVPN-PreAuth-Handler` (반드시 AWSClientVPN- 접두사 사용)
3. `lambda/lambda_function.py` 코드를 복사해서 붙여넣기
4. 환경변수 설정:
   - `API_ENDPOINT`: ALB 도메인 주소
5. VPC 및 보안 그룹 설정

### 4. AWS 인프라 설정

#### Application Load Balancer (ALB)
```bash
# 타겟 그룹 생성
aws elbv2 create-target-group \
  --name vpn-2fa-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id your-vpc-id \
  --health-check-path /api/auth/health/

# ALB 생성
aws elbv2 create-load-balancer \
  --name vpn-2fa-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# 리스너 생성
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

#### Client VPN 설정
1. AWS Client VPN 엔드포인트 생성
2. Active Directory 연동 설정
3. Lambda 함수를 Pre-Authentication Handler로 등록

### 5. 보안 그룹 설정

#### ALB 보안 그룹
- 인바운드: 80, 443 포트 (0.0.0.0/0)
- 아웃바운드: All traffic

#### EC2 보안 그룹  
- 인바운드: 8000 포트 (ALB 보안 그룹에서만)
- 인바운드: 22 포트 (관리자 IP에서만)
- 아웃바운드: All traffic

## 🔧 운영 관리

### Django 서버 시작
```bash
# 개발용
python manage.py runserver 0.0.0.0:8000

# 운영용 (Gunicorn 권장)
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 vpn_auth_backend.wsgi:application
```

### 시스템 서비스 등록 (선택사항)
```bash
# systemd 서비스 파일 생성
sudo nano /etc/systemd/system/vpn-2fa.service

# 서비스 활성화
sudo systemctl enable vpn-2fa
sudo systemctl start vpn-2fa
```

### 모니터링
- Django Admin: http://your-alb-domain/admin/
- Health Check: http://your-alb-domain/api/auth/health/
- 2FA 설정: http://your-alb-domain/

## 📊 사용자 워크플로우

1. **VPN 연결 시도** → Active Directory 인증
2. **2FA 미설정 시** → Lambda가 웹 URL 제공
3. **2FA 설정** → QR 코드 스캔 → 토큰 검증
4. **이후 자동 인증** → 설정된 사용자는 자동 허용

## 🛡️ 보안 권장사항

1. **HTTPS 적용** - ALB에 SSL 인증서 설정
2. **WAF 적용** - 웹 공격 차단
3. **VPC 격리** - Private 서브넷에 EC2 배치
4. **로그 모니터링** - CloudWatch 로그 수집
5. **정기 백업** - 데이터베이스 백업 자동화

## 🚨 문제 해결

### 일반적인 오류
- **500 Error**: DEBUG=True로 설정하여 상세 에러 확인
- **Static Files 404**: `python manage.py collectstatic` 실행
- **DB Error**: 마이그레이션 재실행 `python manage.py migrate`
- **Lambda Timeout**: VPC 내 DNS 설정 확인

### 로그 확인
```bash
# Django 로그
tail -f django.log

# 시스템 로그 (systemd 사용 시)
sudo journalctl -u vpn-2fa -f
```

---

**⚠️ 중요**: 운영 환경 배포 전 반드시 보안 검토를 받으시기 바랍니다.