from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

# 1. إنشاء مدير المستخدمين المخصص
class UserManager(BaseUserManager):
    """
    مدير مخصص لنموذج المستخدم يعتمد على البريد الإلكتروني بدلاً من اسم المستخدم.
    """
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, first_name, last_name, password, **extra_fields)


# 2. نموذج المستخدم الخاص بنا
class User(AbstractUser):
    username = None  # إزالة حقل اسم المستخدم
    email = models.EmailField(_('email address'), unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # ربط النموذج بالمدير المخصص الذي أنشأناه بالأعلى
    objects = UserManager()

    def __str__(self):
        return self.email