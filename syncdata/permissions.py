# syncdata/permissions.py

from rest_framework.permissions import BasePermission

class TokenOnlyPermission(BasePermission):
    """
    Allows access only if a valid token is present.
    """

def has_permission(self, request, view):
    token = request.auth
    return isinstance(token, dict) and 'user_id' in token and 'client_id' in token
