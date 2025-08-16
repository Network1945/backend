# rooms/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, name, password=None, **extra_fields):
        if not name:
            raise ValueError("The 'name' must be set")
        name = self.model.normalize_username(name)  # 공백/케이싱 정리
        user = self.model(name=name, **extra_fields)
        user.set_password(password)  # 해시 저장
        user.save(using=self._db)
        return user

    def create_superuser(self, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    # 로그인 ID로 쓸 필드
    name = models.CharField("Name", max_length=100, unique=True)

    # 최소 권한 필드
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "name"   # ← 로그인 식별자
    REQUIRED_FIELDS = []      # ← createsuperuser 시 추가 입력 필드 없음

    objects = UserManager()

    def __str__(self):
        return self.name


# rooms/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

# rooms/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

def short_id():
    # lambda 대신 최상단 함수로 분리해야 직렬화 가능
    return uuid.uuid4().hex[:8]

class Room(models.Model):
    class Status(models.TextChoices):
        LOBBY = "lobby", "Lobby"
        RUNNING = "running", "Running"
        ENDED = "ended", "Ended"

    id = models.CharField(
        primary_key=True,
        max_length=12,
        editable=False,
        default=short_id,                  # ← lambda 금지, 함수 참조 OK
        unique=True,
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_rooms",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.LOBBY)
    created_at = models.DateTimeField(default=timezone.now)

    name = models.CharField(max_length=50, help_text="방 이름")  # 방 이름
    password = models.CharField(max_length=128, blank=True, null=True, help_text="비밀번호")  # 방 비밀번호 (없을 수도 있음)

    def __str__(self):
        return f"Room({self.id})"