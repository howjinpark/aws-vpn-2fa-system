from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
import csv

class Command(BaseCommand):
    help = '그룹별로 VPN 사용자를 일괄 생성합니다'

    def add_arguments(self, parser):
        parser.add_argument('--group', type=str, required=True, help='그룹명')
        parser.add_argument('--users', type=str, required=True, help='사용자명 (쉼표로 구분)')
        parser.add_argument('--csv-file', type=str, help='CSV 파일에서 사용자 가져오기')

    @transaction.atomic
    def handle(self, *args, **options):
        group_name = options['group']
        
        # 그룹 생성 또는 가져오기
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'그룹 "{group_name}"이 생성되었습니다.')
            )
        else:
            self.stdout.write(f'기존 그룹 "{group_name}"을 사용합니다.')

        users_created = 0
        users_added_to_group = 0

        # CSV 파일 처리
        if options.get('csv_file'):
            try:
                with open(options['csv_file'], 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader)  # 헤더 건너뛰기
                    usernames = [row[0] for row in reader if row]
            except FileNotFoundError:
                self.stdout.write(
                    self.style.ERROR(f'CSV 파일을 찾을 수 없습니다: {options["csv_file"]}')
                )
                return
        else:
            # 직접 입력된 사용자명 처리
            usernames = [username.strip() for username in options['users'].split(',')]

        # 사용자 생성 및 그룹 할당
        for username in usernames:
            if not username:
                continue
                
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@company.com',
                    'is_active': True,
                }
            )
            
            # VPN 전용 계정은 Django 로그인 불가능하도록 설정
            if user_created and not user.is_superuser:
                user.set_unusable_password()
                user.save()
            
            if user_created:
                users_created += 1
                self.stdout.write(f'사용자 "{username}" 생성됨')
            
            # 그룹에 추가
            if not user.groups.filter(name=group_name).exists():
                user.groups.add(group)
                users_added_to_group += 1
                self.stdout.write(f'사용자 "{username}"를 그룹 "{group_name}"에 추가함')

        self.stdout.write(
            self.style.SUCCESS(
                f'완료! 생성된 사용자: {users_created}명, 그룹 추가: {users_added_to_group}명'
            )
        )