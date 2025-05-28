from rest_framework import permissions


class IsBarbershopOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение на изменение только владельцу барбершопа
    """

    def has_object_permission(self, request, view, obj):
        # Чтение разрешено всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # Изменение только владельцу
        return obj.owner == request.user