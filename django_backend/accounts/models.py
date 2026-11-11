from django.db import models
from django.db.models import Q


class User(models.Model):
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=16, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password_hash = models.TextField()
    is_active = models.BooleanField(default=True, db_default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_authenticated(self):
        return True

    class Meta:
        db_table = "users"
        constraints = [models.CheckConstraint(condition=Q(is_active__in=[True, False]), name="ck_users_is_active")]


class AuthSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="auth_sessions")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auth_sessions"
