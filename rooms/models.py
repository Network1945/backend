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