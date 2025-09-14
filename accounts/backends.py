from django.contrib.auth.backends import BaseBackend
from .models import User

class MobileBackend(BaseBackend):
    def authenticate(self, request, mobile=None, **kwargs):
        try:
            user = User.objects.get(mobile=mobile)
            return user
        except User.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None