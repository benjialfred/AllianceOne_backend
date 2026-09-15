from rest_framework import permissions

class IsFounderOrAdmin(permissions.BasePermission):
    """
    Permission permettant l'accès uniquement au Fondateur 
    (benjaminadzessa@gmail.com) ou aux administrateurs (is_staff/is_superuser).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        if user.is_superuser or user.is_staff:
            return True
            
        if user.email == 'benjaminadzessa@gmail.com':
            return True
            
        return False
