from datetime import timedelta
from secrets import token_urlsafe

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import token_digest
from accounts.models import AuthSession, User
from accounts.serializers import LoginSerializer, RegistrationSerializer, UserSerializer
from accounts.throttles import LoginThrottle
from config.errors import Conflict


# Precompute at startup so the first unknown user does not take an extra hash.
DUMMY_PASSWORD_HASH = make_password(token_urlsafe(32), hasher="argon2")


class AuthView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class RegisterView(AuthView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data.get("email") or None
        try:
            with transaction.atomic():
                user = User.objects.create(full_name=data["full_name"], phone=data["phone"], email=email, password_hash=make_password(data["password"], hasher="argon2"))
        except IntegrityError:
            if User.objects.filter(phone=data["phone"]).exists() or (email and User.objects.filter(email=email).exists()):
                raise Conflict("Phone or email is already registered.")
            raise
        return Response(UserSerializer(user).data, status=201)


class LoginView(AuthView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(phone=data["phone"]).first()
        encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_ok = check_password(data["password"], encoded)
        if not user or not user.is_active or not password_ok:
            raise AuthenticationFailed("Invalid or expired credentials.")
        token = token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=settings.SESSION_TTL_HOURS)
        AuthSession.objects.create(user=user, token_hash=token_digest(token.encode("ascii")), expires_at=expires_at)
        return Response({"access_token": token, "token_type": "bearer", "expires_at": expires_at.isoformat().replace("+00:00", "Z")})


class MeView(AuthView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(AuthView):
    def post(self, request):
        AuthSession.objects.filter(pk=request.auth.pk, revoked_at__isnull=True).update(revoked_at=timezone.now(), updated_at=timezone.now())
        return Response(status=204)
