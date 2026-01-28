from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from ..managers import UserManager


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CLIENT = "client", "Client"


class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()
    username = models.CharField(max_length=150, unique=True, null=False)
    email = models.EmailField(max_length=255, unique=True, null=False)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.CLIENT,
        null=False,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True, null=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["role"], name="idx_users_role"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=UserRole.values),
                name="check_valid_user_role",
            )
        ]

    def __str__(self):
        return self.username
