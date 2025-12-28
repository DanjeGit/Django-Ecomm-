from rest_framework import serializers
from django.contrib.auth.models import User
from .models import WasteItem, Category, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class WasteItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    seller_name = serializers.CharField(source='seller.business_name', read_only=True)

    class Meta:
        model = WasteItem
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6)
