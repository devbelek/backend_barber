from rest_framework import permissions


class IsClientOrBarberOwner(permissions.BasePermission):
    """
    Разрешение для работы с бронированиями:
    - Клиент может изменять свои бронирования
    - Барбер может изменять бронирования на свои услуги
    """

    def has_object_permission(self, request, view, obj):
        # Проверяем, является ли пользователь клиентом, который создал бронирование
        if obj.client == request.user:
            return True

        # Проверяем, является ли пользователь барбером, предоставляющим услугу
        if obj.service.barber == request.user:
            return True

        return False