import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import AuthSession


def token_digest(token):
    return hashlib.sha256(token).hexdigest()


class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer" or len(header[1]) > 1024:
            raise AuthenticationFailed("Invalid or expired credentials.")
        session = AuthSession.objects.select_related("user").filter(token_hash=token_digest(header[1])).first()
        if session is None or session.revoked_at is not None or session.expires_at <= timezone.now() or not session.user.is_active:
            raise AuthenticationFailed("Invalid or expired credentials.")
        return session.user, session

    def authenticate_header(self, request):
        return "Bearer"
