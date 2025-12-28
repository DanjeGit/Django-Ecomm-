from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, User, Transaction, Order, BuyerProfile, Cart
import json

@shared_task
def process_mpesa_callback_task(callback_data):
    """
    Background task to process M-Pesa callback logic.
    """
    print("🔄 [Celery] Processing M-Pesa Callback...")
    
    try:
        # Extract details
        body = callback_data.get('Body', {})
        stk_cb = body.get('stkCallback', {})
        result_code = stk_cb.get('ResultCode')
        checkout_request_id = stk_cb.get('CheckoutRequestID')
        metadata = stk_cb.get('CallbackMetadata', {})
        items = metadata.get('Item', []) if isinstance(metadata, dict) else []

        amount = None
        phone = None
        mpesa_name = ''
        mpesa_receipt_number = None
        
        for it in items:
            name = it.get('Name')
            val = it.get('Value')
            if name == 'Amount':
                amount = val
            elif name == 'MpesaReceiptNumber':
                mpesa_receipt_number = str(val)
            elif name in ('PhoneNumber', 'MSISDN'):
                phone = str(val)
            elif name in ('FirstName', 'MiddleName', 'LastName'):
                mpesa_name = (mpesa_name + ' ' + str(val)).strip()

        # Find user
        user = None
        if phone:
            try:
                bp = BuyerProfile.objects.get(phone_number=phone)
                user = bp.user
            except BuyerProfile.DoesNotExist:
                user = None

        # Update Transaction
        if checkout_request_id:
            tx = Transaction.objects.filter(checkout_request_id=checkout_request_id).first()

            if tx:
                if result_code == 0:
                    tx.state = 'confirmed'
                    
                    # Determine the best available name
                    final_name = mpesa_name
                    if not final_name and user:
                        final_name = user.get_full_name() or user.username
                    
                    # Only update if we found a valid name, otherwise keep the one from creation
                    if final_name:
                        tx.mpesa_name = final_name
                        
                    tx.phone_number = phone or tx.phone_number
                    tx.mpesa_receipt_number = mpesa_receipt_number
                    tx.save()
                    
                    # Update Order
                    if tx.order:
                        tx.order.status = 'confirmed'
                        tx.order.save()
                        
                        # Reduce stock
                        for order_item in tx.order.items.all():
                            if order_item.item:
                                try:
                                    current_stock = int(order_item.item.stock_quantity)
                                    new_stock = max(0, current_stock - order_item.quantity)
                                    order_item.item.stock_quantity = str(new_stock)
                                    order_item.item.save()
                                except ValueError:
                                    pass
                        
                        # Trigger Notifications (Import locally to avoid circular dependency if needed)
                        from .views import send_seller_notifications, send_buyer_order_confirmation
                        send_seller_notifications(tx.order)
                        send_buyer_order_confirmation(tx.order)

                    # Clear Cart
                    try:
                        # Use the user from the order, which is more reliable than phone lookup
                        cart_user = tx.order.user if tx.order else user
                        if cart_user:
                            cart = Cart.objects.get(user=cart_user)
                            cart.items.all().delete()
                            print(f"✅ [Celery] Cart cleared for user {cart_user.username}")
                    except Cart.DoesNotExist:
                        pass
                else:
                    tx.state = 'cancelled'
                    tx.mpesa_name = mpesa_name or (user.get_full_name() if user else '')
                    tx.phone_number = phone or tx.phone_number
                    tx.save()
                    if tx.order:
                        tx.order.status = 'cancelled'
                        tx.order.save()
        
        return "Callback processed successfully"

    except Exception as e:
        print(f"❌ [Celery] Callback Processing Failed: {e}")
        return f"Error: {e}"

@shared_task
def send_email_task(subject, message, recipient_list, html_message=None):
    """
    Background task to send an email.
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
            html_message=html_message
        )
        return f"Email sent to {recipient_list}"
    except Exception as e:
        print(f"❌ EMAIL TASK FAILED: {e}")
        return f"Failed to send email: {e}"

@shared_task
def create_notification_task(user_id, title, message, link=None):
    """
    Background task to create a notification.
    """
    try:
        user = User.objects.get(id=user_id)
        Notification.objects.create(user=user, title=title, message=message, link=link)
        return f"Notification created for {user.username}"
    except User.DoesNotExist:
        return "User not found"
