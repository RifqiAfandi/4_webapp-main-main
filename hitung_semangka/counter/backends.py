# counter/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            # Cari user berdasarkan email
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        else:
            # Jika user ditemukan, cek passwordnya
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None