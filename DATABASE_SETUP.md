# 📊 데이터베이스 설정 가이드

이 프로젝트는 **SQLite**를 사용하여 데이터를 저장합니다. 별도의 데이터베이스 서버 설치가 필요하지 않습니다.

## 🗄️ 데이터베이스 구조

### 주요 테이블
```sql
-- 사용자 2FA 정보
authentication_usertwofactorauth
├─ user_id: Django 사용자 연결
├─ secret_key: TOTP 비밀키 (Google Authenticator용)
├─ is_enabled: 2FA 활성화 여부
└─ created_at: 생성 일시

-- VPN 접속 로그
authentication_vpnaccesslog
├─ user_id: 사용자 ID
├─ username: 사용자명
├─ client_ip: 접속 IP (개인정보 보호를 위해 마스킹됨)
├─ two_factor_verified: 2FA 인증 성공 여부
├─ access_granted: VPN 접근 허용 여부
└─ access_time: 접속 시도 시간

-- 그룹별 시간 제한 정책
authentication_vpngrouppolicy
├─ group_id: Django 그룹 연결
├─ enable_time_restriction: 시간 제한 사용 여부
├─ allowed_start_time: 허용 시작 시간
├─ allowed_end_time: 허용 종료 시간
├─ allowed_weekdays: 허용 요일 (1=월요일, 7=일요일)
└─ timezone: 시간대 설정
```

## 🚀 데이터베이스 초기 설정

### 1단계: 환경 설정
```bash
cd backend
source venv/bin/activate  # 가상환경 활성화
```

### 2단계: 데이터베이스 생성 및 마이그레이션
```bash
# Django 마이그레이션 파일 생성 (이미 생성됨)
python manage.py makemigrations

# 데이터베이스 테이블 생성
python manage.py migrate

# 생성 확인
ls -la db.sqlite3
```

### 3단계: 관리자 계정 생성
```bash
python manage.py createsuperuser
```
다음 정보를 입력하세요:
- **Username**: 관리자 사용자명
- **Email**: 관리자 이메일 (선택사항)
- **Password**: 안전한 비밀번호

### 4단계: 초기 데이터 확인
```bash
# Django shell에서 데이터 확인
python manage.py shell

# Shell에서 실행:
>>> from django.contrib.auth.models import User
>>> from authentication.models import UserTwoFactorAuth
>>> User.objects.all()  # 생성된 사용자 확인
>>> UserTwoFactorAuth.objects.all()  # 2FA 설정 확인
>>> exit()
```

## 🔧 개발 중 유용한 명령어

### 데이터베이스 초기화 (주의: 모든 데이터 삭제됨)
```bash
# 데이터베이스 파일 삭제
rm db.sqlite3

# 마이그레이션 재실행
python manage.py migrate

# 관리자 계정 재생성
python manage.py createsuperuser
```

### 테스트 데이터 생성
```bash
# Django shell에서 테스트 사용자 생성
python manage.py shell

>>> from django.contrib.auth.models import User, Group
>>> from authentication.models import UserTwoFactorAuth, VPNGroupPolicy

# 테스트 사용자 생성
>>> user = User.objects.create_user('testuser@your-domain.com', password='testpass123')

# VPN 사용자 그룹 생성
>>> vpn_group = Group.objects.create(name='VPNUsers')
>>> user.groups.add(vpn_group)

# 2FA 설정 생성 (비활성화 상태)
>>> auth_2fa = UserTwoFactorAuth.objects.create(user=user, is_enabled=False)

# 시간 제한 정책 생성 (평일 9-18시)
>>> policy = VPNGroupPolicy.objects.create(
...     group=vpn_group,
...     enable_time_restriction=True,
...     allowed_start_time='09:00:00',
...     allowed_end_time='18:00:00', 
...     allowed_weekdays='1,2,3,4,5',  # 월-금
...     timezone='Asia/Seoul'
... )

>>> exit()
```

## 📋 데이터베이스 백업 및 복원

### 백업
```bash
# SQLite 파일 복사 (가장 간단)
cp db.sqlite3 backup_$(date +%Y%m%d_%H%M%S).sqlite3

# 또는 SQL 덤프 생성
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

### 복원
```bash
# SQLite 파일 복원
cp backup_20240123_143022.sqlite3 db.sqlite3

# 또는 JSON 덤프 복원
python manage.py loaddata backup_20240123_143022.json
```

## 🔍 데이터베이스 직접 조회

### SQLite 명령줄 도구 사용
```bash
# SQLite shell 접속
python manage.py dbshell

# SQL 쿼리 실행
.tables  -- 모든 테이블 보기
.schema authentication_usertwofactorauth  -- 테이블 구조 보기

SELECT * FROM auth_user;  -- 사용자 목록
SELECT * FROM authentication_usertwofactorauth;  -- 2FA 설정
SELECT * FROM authentication_vpnaccesslog ORDER BY access_time DESC LIMIT 10;  -- 최근 로그

.quit  -- 종료
```

### Django Admin에서 조회
```bash
# 서버 실행
python manage.py runserver 0.0.0.0:8000

# 브라우저에서 접속
http://localhost:8000/admin/

# 생성한 관리자 계정으로 로그인
```

## ⚠️ 주의사항

### 운영 환경에서
- **데이터베이스 파일 권한** 설정: `chmod 600 db.sqlite3`
- **정기 백업** 설정: cron으로 자동 백업 스케줄 설정
- **로그 파일 크기** 관리: VPN 접속 로그가 계속 쌓이므로 주기적 정리 필요

### 개발 환경에서
- **민감한 데이터** 주의: 실제 사용자 정보를 테스트에 사용하지 말 것
- **마이그레이션 파일** 관리: 스키마 변경 시 마이그레이션 파일 커밋 필수

## 🔧 문제 해결

### 일반적인 오류
```bash
# "no such table" 오류
python manage.py migrate

# "database is locked" 오류  
lsof db.sqlite3  # 사용 중인 프로세스 확인
killall python   # Django 서버 종료 후 재시작

# 권한 오류
chown $USER:$USER db.sqlite3
chmod 644 db.sqlite3
```

---

SQLite는 파일 기반 데이터베이스이므로 설정이 매우 간단합니다. 위 가이드를 따라하면 완전한 데이터베이스 환경을 구축할 수 있습니다!