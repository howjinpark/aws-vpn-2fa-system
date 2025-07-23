#!/bin/bash

# AWS VPN 2FA 시스템 배포 스크립트
# Private EC2에서 Django 백엔드와 React 프론트엔드를 배포하는 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 스크립트 위치 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "프로젝트 디렉토리: $PROJECT_ROOT"

# 백엔드 배포
deploy_backend() {
    log_info "Django 백엔드 배포를 시작합니다..."
    
    cd "$PROJECT_ROOT/backend"
    
    # 가상환경 활성화
    source venv/bin/activate
    
    # 의존성 설치
    log_info "Python 의존성 설치 중..."
    pip install -r requirements.txt || {
        log_warn "requirements.txt 파일이 없습니다. 기본 패키지를 설치합니다."
        pip install django djangorestframework django-cors-headers pyotp qrcode[pil]
    }
    
    # 데이터베이스 마이그레이션
    log_info "데이터베이스 마이그레이션 실행 중..."
    python manage.py makemigrations
    python manage.py migrate
    
    # 슈퍼유저 생성 (환경변수 또는 대화형으로)
    log_info "관리자 계정 확인 중..."
    
    # 환경변수에서 관리자 정보 확인
    ADMIN_USERNAME=\${ADMIN_USERNAME:-""}
    ADMIN_EMAIL=\${ADMIN_EMAIL:-""}
    ADMIN_PASSWORD=\${ADMIN_PASSWORD:-""}
    
    if [[ -n "\$ADMIN_USERNAME" && -n "\$ADMIN_EMAIL" && -n "\$ADMIN_PASSWORD" ]]; then
        python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='\$ADMIN_USERNAME').exists():
    User.objects.create_superuser('\$ADMIN_USERNAME', '\$ADMIN_EMAIL', '\$ADMIN_PASSWORD')
    print('관리자 계정이 생성되었습니다: \$ADMIN_USERNAME')
else:
    print('관리자 계정이 이미 존재합니다: \$ADMIN_USERNAME')
"
    else
        log_warn "관리자 계정 정보가 환경변수에 설정되지 않았습니다."
        log_warn "수동으로 'python manage.py createsuperuser' 명령을 실행하세요."
    fi
    
    # 정적 파일 수집
    log_info "정적 파일 수집 중..."
    python manage.py collectstatic --noinput || log_warn "정적 파일 수집 중 오류 발생"
    
    log_info "Django 백엔드 배포 완료!"
}

# 프론트엔드 배포
deploy_frontend() {
    log_info "React 프론트엔드 배포를 시작합니다..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # 의존성 설치
    log_info "Node.js 의존성 설치 중..."
    npm install
    
    # 빌드
    log_info "React 앱 빌드 중..."
    npm run build
    
    log_info "React 프론트엔드 배포 완료!"
}

# 시스템 서비스 설정
setup_services() {
    log_info "시스템 서비스를 설정합니다..."
    
    # Django 서비스 파일 생성
    sudo tee /etc/systemd/system/vpn-auth-backend.service > /dev/null <<EOF
[Unit]
Description=VPN Auth Backend
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=$PROJECT_ROOT/backend
Environment=PATH=$PROJECT_ROOT/backend/venv/bin
ExecStart=$PROJECT_ROOT/backend/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # 서비스 활성화 및 시작
    sudo systemctl daemon-reload
    sudo systemctl enable vpn-auth-backend.service
    sudo systemctl start vpn-auth-backend.service
    
    log_info "Django 백엔드 서비스가 시작되었습니다."
    
    # 프론트엔드를 위한 Nginx 설정 (선택사항)
    if command -v nginx &> /dev/null; then
        log_info "Nginx 설정을 업데이트합니다..."
        
        sudo tee /etc/nginx/sites-available/vpn-auth > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;
    
    # React 프론트엔드
    location / {
        root $PROJECT_ROOT/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Django API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Django Admin
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        
        # 사이트 활성화
        sudo ln -sf /etc/nginx/sites-available/vpn-auth /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
        
        log_info "Nginx 설정이 완료되었습니다."
    else
        log_warn "Nginx가 설치되어 있지 않습니다. 수동으로 웹서버를 설정해주세요."
    fi
}

# 방화벽 설정
setup_firewall() {
    if command -v ufw &> /dev/null; then
        log_info "방화벽 규칙을 설정합니다..."
        
        sudo ufw allow 22     # SSH
        sudo ufw allow 80     # HTTP
        sudo ufw allow 443    # HTTPS
        sudo ufw allow 8000   # Django
        
        log_info "방화벽 규칙 설정 완료."
    else
        log_warn "UFW가 설치되어 있지 않습니다. 방화벽을 수동으로 설정해주세요."
    fi
}

# 상태 확인
check_status() {
    log_info "서비스 상태를 확인합니다..."
    
    # Django 서비스 상태
    if systemctl is-active --quiet vpn-auth-backend.service; then
        log_info "✓ Django 백엔드 서비스가 실행 중입니다."
    else
        log_error "✗ Django 백엔드 서비스가 실행되지 않고 있습니다."
    fi
    
    # 포트 확인
    if netstat -tuln | grep -q ":8000 "; then
        log_info "✓ Django가 포트 8000에서 실행 중입니다."
    else
        log_error "✗ Django가 포트 8000에서 실행되지 않고 있습니다."
    fi
    
    # Nginx 상태 (있는 경우)
    if command -v nginx &> /dev/null && systemctl is-active --quiet nginx; then
        log_info "✓ Nginx가 실행 중입니다."
    fi
}

# 메인 배포 함수
main() {
    log_info "AWS VPN 2FA 시스템 배포를 시작합니다..."
    
    # 권한 확인
    if [[ $EUID -ne 0 ]]; then
        log_warn "이 스크립트는 root 권한이 필요한 부분이 있습니다. sudo 권한이 필요할 수 있습니다."
    fi
    
    # 배포 단계
    case "${1:-all}" in
        "backend")
            deploy_backend
            ;;
        "frontend")
            deploy_frontend
            ;;
        "services")
            setup_services
            ;;
        "firewall")
            setup_firewall
            ;;
        "status")
            check_status
            ;;
        "all")
            deploy_backend
            deploy_frontend
            setup_services
            setup_firewall
            check_status
            ;;
        *)
            echo "사용법: $0 [backend|frontend|services|firewall|status|all]"
            echo ""
            echo "  backend   - Django 백엔드만 배포"
            echo "  frontend  - React 프론트엔드만 배포"
            echo "  services  - 시스템 서비스 설정"
            echo "  firewall  - 방화벽 설정"
            echo "  status    - 서비스 상태 확인"
            echo "  all       - 전체 배포 (기본값)"
            exit 1
            ;;
    esac
    
    log_info "배포가 완료되었습니다!"
    log_info "접속 정보:"
    log_info "  - 프론트엔드: http://$(hostname -I | awk '{print $1}')/"
    log_info "  - 백엔드 API: http://$(hostname -I | awk '{print $1}'):8000/api/"
    log_info "  - Django Admin: http://$(hostname -I | awk '{print $1}'):8000/admin/"
}

# 스크립트 실행
main "$@"