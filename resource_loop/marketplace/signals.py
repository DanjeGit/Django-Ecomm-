from django.db.models.signals import pre_save, post_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import Order, Notification, ActivityLog
from django.urls import reverse
from .tasks import send_email_task

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    ActivityLog.objects.create(
        user=user,
        action='login',
        description=f"User {user.username} logged in.",
        ip_address=ip
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    if user:
        ActivityLog.objects.create(
            user=user,
            action='logout',
            description=f"User {user.username} logged out.",
            ip_address=ip
        )

@receiver(pre_save, sender=Order)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture the old status before saving the order to check for changes.
    """
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Order)
def notify_order_status_change(sender, instance, created, **kwargs):
    """
    Send a notification when the order status changes.
    """
    old_status = getattr(instance, '_old_status', None)
    
    if not old_status or old_status == instance.status:
        return

    # Order Delivered
    if instance.status == 'delivered':
        Notification.objects.create(
            user=instance.user,
            title="Order Delivered",
            message=f"Your order #{instance.order_uuid} has been delivered successfully.",
            link=reverse('order_detail', args=[instance.id])
        )
        
        # Send Email
        try:
            pickup_info = ""
            if instance.pickup_station:
                pickup_info = f"\n\nPickup Station: {instance.pickup_station.name}\nAddress: {instance.pickup_station.address}\n\nPlease pick up your item within 7 working days."
            
            send_email_task.delay(
                subject="Order Delivered - Resource Loop",
                message=f"Hello {instance.user.username},\n\nYour order #{instance.order_uuid} has been delivered successfully.{pickup_info}\n\nThank you for shopping with us!",
                recipient_list=[instance.user.email]
            )
        except Exception as e:
            print(f"Failed to send delivery email: {e}")

    # Order Shipped
    elif instance.status == 'shipped':
        Notification.objects.create(
            user=instance.user,
            title="Order Shipped",
            message=f"Your order #{instance.order_uuid} is on its way!",
            link=reverse('order_detail', args=[instance.id])
        )
        try:
            send_email_task.delay(
                subject="Order Shipped - Resource Loop",
                message=f"Hello {instance.user.username},\n\nYour order #{instance.order_uuid} has been shipped and is on its way.\n\nTrack your order in the dashboard.",
                recipient_list=[instance.user.email]
            )
        except Exception as e:
            print(f"Failed to send shipped email: {e}")

    # Order Cancelled
    elif instance.status == 'cancelled':
        Notification.objects.create(
            user=instance.user,
            title="Order Cancelled",
            message=f"Your order #{instance.order_uuid} has been cancelled.",
            link=reverse('order_detail', args=[instance.id])
        )
        try:
            send_email_task.delay(
                subject="Order Cancelled - Resource Loop",
                message=f"Hello {instance.user.username},\n\nYour order #{instance.order_uuid} has been cancelled.\n\nIf you did not request this, please contact support.",
                recipient_list=[instance.user.email]
            )
        except Exception as e:
            print(f"Failed to send cancelled email: {e}")
