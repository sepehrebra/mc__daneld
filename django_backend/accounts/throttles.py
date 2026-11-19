import hashlib

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle


class LoginThrottle(BaseThrottle):
    """Fixed window per direct peer; local cache is per process."""
    limit = 10
    duration = 600

    def allow_request(self, request, view):
        peer = request.META.get("REMOTE_ADDR", "unknown")
        key = "login-rate:" + hashlib.sha256(peer.encode()).hexdigest()
        if cache.add(key, 1, timeout=self.duration):
            return True
        try:
            return cache.incr(key) <= self.limit
        except ValueError:
            # A window expired between add and incr; begin a new one.
            return cache.add(key, 1, timeout=self.duration)

    def wait(self):
        return self.duration
