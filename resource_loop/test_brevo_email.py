import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resource_loop.settings')
django.setup()

def test_email():
    print("Attempting to send email via Brevo...")
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"API Key present: {bool(settings.ANYMAIL.get('BREVO_API_KEY'))}")

    try:
        send_mail(
            'Brevo Test Email',
            'This is a test email from your Django app using Brevo API.',
            settings.DEFAULT_FROM_EMAIL,
            ['njd563347@gmail.com'], # Sending to self for test
            fail_silently=False,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email failed: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.content}")

if __name__ == "__main__":
    test_email()
