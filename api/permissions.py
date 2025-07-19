from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.conf import settings

class ReadOnlyOrTokenPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        token = request.headers.get('Authorization')
        if not token:
            return False
        if token.startswith('Token '):
            token_key = token.split(' ', 1)[1]
            return token_key == settings.API_TOKEN
        return False 