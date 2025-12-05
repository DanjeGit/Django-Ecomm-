from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import BuyerProfile

class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Try to fetch the user by email
            user = UserModel.objects.get(email__iexact=username)
        except UserModel.DoesNotExist:
            try:
                # Try to fetch the user by username
                user = UserModel.objects.get(username__iexact=username)
            except UserModel.DoesNotExist:
                # If user is not found by email or username, try phone number
                try:
                    # Find the profile by phone number, then get the associated user
                    profile = BuyerProfile.objects.get(phone_number=username)
                    user = profile.user
                except BuyerProfile.DoesNotExist:
                    # No user found for the given credentials
                    return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
