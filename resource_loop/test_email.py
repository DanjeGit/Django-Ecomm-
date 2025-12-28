import os
import django
from django.core.mail import send_mail
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resource_loop.settings')
django.setup()

def test_email():
    print("Attempting to send email...")
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"User: {settings.EMAIL_HOST_USER}")
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    
    try:
        send_mail(
            subject='Test Email from Resource Loop',
            message='If you see this, email configuration is working!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER], # Send to self
            fail_silently=False,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    test_email()
