from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        login_value = kwargs.get(UserModel.USERNAME_FIELD, username)
        if not login_value or not password:
            return None

        try:
            user = UserModel.objects.get(email__iexact=login_value)
        except UserModel.DoesNotExist:
            try:
                user = UserModel.objects.get(username=login_value)
            except UserModel.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

