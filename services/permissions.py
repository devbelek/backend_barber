from rest_framework import permissions


class IsBarberOrReadOnly(permissions.BasePermission):
    """
    Разрешение на запись только барберам, чтение - всем
    """

    def has_permission(self, request, view):
        # Разрешить GET, HEAD, OPTIONS всем пользователям
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешить POST, PUT, DELETE только барберам
        return request.user.is_authenticated and hasattr(request.user,
                                                         'profile') and request.user.profile.user_type == 'barber'

    def has_object_permission(self, request, view, obj):
        # Разрешить GET, HEAD, OPTIONS всем пользователям
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешить изменение и удаление только владельцу
        return obj.barber == request.user