from django import forms
from django.contrib.auth.models import User
from .models import BuyerProfile, SellerProfile
import phonenumbers
from django.core.exceptions import ValidationError
from .locations import KENYA_LOCATIONS

class UserForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_password', 'placeholder': 'Password', 'autocomplete': 'new-password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

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

from .models import BuyerProfile, SellerProfile, PickupStation

class BuyerProfileForm(forms.ModelForm):
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0712345678', 'maxlength': '10'}))
    
    # Create choices for County
    COUNTY_CHOICES = [('', 'Select County')] + [(c, c) for c in sorted(KENYA_LOCATIONS.keys())]
    
    county = forms.ChoiceField(
        choices=COUNTY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_county'})
    )
    
    sub_county = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_sub_county'}),
        required=True
    )

    pickup_station = forms.ModelChoiceField(
        queryset=PickupStation.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_pickup_station'}),
        empty_label="Select Pickup Station (Optional)"
    )

    class Meta:
        model = BuyerProfile
        fields = ('phone_number', 'county', 'sub_county', 'pickup_station')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate pickup stations if sub_county is selected
        if 'sub_county' in self.data:
            try:
                sub_county = self.data.get('sub_county')
                self.fields['pickup_station'].queryset = PickupStation.objects.filter(sub_county=sub_county)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.sub_county:
            self.fields['pickup_station'].queryset = PickupStation.objects.filter(sub_county=self.instance.sub_county)
        # If we have bound data (POST), populate sub_county choices so validation passes
        if 'county' in self.data:
            try:
                county = self.data.get('county')
                sub_counties = KENYA_LOCATIONS.get(county, [])
                self.fields['sub_county'].widget.choices = [(sc, sc) for sc in sub_counties]
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.county:
            # If editing an existing profile, populate sub_counties for the selected county
            sub_counties = KENYA_LOCATIONS.get(self.instance.county, [])
            self.fields['sub_county'].widget.choices = [(sc, sc) for sc in sub_counties]
        else:
            self.fields['sub_county'].widget.choices = [('', 'Select County First')]

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        try:
            parsed_number = phonenumbers.parse(phone_number, "KE") # Assuming Kenya as default region
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValidationError("Invalid phone number.")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValidationError("Invalid phone number format.")
        return phone_number

class SellerProfileForm(forms.ModelForm):
    business_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business Name'}))
    payment_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M-Pesa Number (e.g., 0712345678)'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Tell us about your business...', 'rows': 3}))
    profile_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # Create choices for County
    COUNTY_CHOICES = [('', 'Select County')] + [(c, c) for c in sorted(KENYA_LOCATIONS.keys())]
    
    county = forms.ChoiceField(
        choices=COUNTY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_county'})
    )
    
    sub_county = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_sub_county'}),
        required=True
    )
    
    class Meta:
        model = SellerProfile
        fields = ('business_name', 'payment_number', 'county', 'sub_county', 'description', 'profile_image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have bound data (POST), populate sub_county choices so validation passes
        if 'county' in self.data:
            try:
                county = self.data.get('county')
                sub_counties = KENYA_LOCATIONS.get(county, [])
                self.fields['sub_county'].widget.choices = [(sc, sc) for sc in sub_counties]
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.county:
            # If editing an existing profile, populate sub_counties for the selected county
            sub_counties = KENYA_LOCATIONS.get(self.instance.county, [])
            self.fields['sub_county'].widget.choices = [(sc, sc) for sc in sub_counties]
        else:
            self.fields['sub_county'].widget.choices = [('', 'Select County First')]
