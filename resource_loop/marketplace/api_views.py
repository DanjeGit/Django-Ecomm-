from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django.shortcuts import get_object_or_404
from .models import WasteItem, Category, Notification, OTP
from .serializers import WasteItemSerializer, CategorySerializer, NotificationSerializer, OTPSerializer
from .tasks import send_email_task
import random
import time
from django.utils import timezone

class OTPRateThrottle(UserRateThrottle):
    scope = 'otp'

class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WasteItem.objects.all()
    serializer_class = WasteItemSerializer
    permission_classes = [permissions.AllowAny]

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

class OTPViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OTPRateThrottle]

    @action(detail=False, methods=['post'])
    def resend(self, request):
        user = request.user
        
        # Check cooldown (e.g., 1 minute)
        last_otp = OTP.objects.filter(user=user).order_by('-created_at').first()
        if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 60:
            return Response(
                {'error': 'Please wait before requesting a new OTP.'}, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Generate new OTP
        code = str(random.randint(100000, 999999))
        OTP.objects.create(user=user, code=code)
        
        # Send Email (Async)
        send_email_task.delay(
            'Your Verification Code',
            f'Your new verification code is: {code}',
            [user.email]
        )
        
        return Response({'status': 'OTP sent'})

    @action(detail=False, methods=['post'])
    def verify(self, request):
        serializer = OTPSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['code']
            user = request.user
            
            # Find valid OTP
            otp = OTP.objects.filter(user=user, code=code, is_used=False).order_by('-created_at').first()
            
            if otp and otp.is_valid():
                otp.is_used = True
                otp.save()
                user.is_active = True
                user.save()
                return Response({'status': 'Verified'})
            
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
