from django import forms
from django.contrib.auth.models import User
from .models import BuyerProfile
import phonenumbers
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_password', 'placeholder': 'Password'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance and self.instance.pk:
            # This is an update, so exclude the current user from the check
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("An account with this email already exists.")
        elif User.objects.filter(email=email).exists():
            # This is a creation, check all users
            raise ValidationError("An account with this email already exists.")
        return email

class BuyerProfileForm(forms.ModelForm):
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0712345678', 'maxlength': '10'}))
    location = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = BuyerProfile
        fields = ('phone_number', 'location')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        try:
            parsed_number = phonenumbers.parse(phone_number, "KE") # Assuming Kenya as default region
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValidationError("Invalid phone number.")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValidationError("Invalid phone number format.")
        return phone_number
