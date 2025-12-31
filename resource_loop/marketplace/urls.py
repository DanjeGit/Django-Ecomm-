from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views
from . import api_utils

router = DefaultRouter()
router.register(r'items', api_views.MarketplaceViewSet)
router.register(r'notifications', api_views.NotificationViewSet, basename='notification')
router.register(r'otp', api_views.OTPViewSet, basename='otp')

urlpatterns = [
    path('debug-static/', views.debug_static_files, name='debug_static'),
    path('', views.index, name='index'),
    path('api/', include(router.urls)),
    path('search/', views.search_results, name='search'),
    path('item/<slug:slug>/', views.item_detail, name='item_detail'),
    path('loop2/', views.loop2_demo, name='loop2_demo'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('dashboard/seller/', views.seller_dashboard, name='seller_dashboard'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/status/', views.payment_status, name='payment_status'),
    path('history/', views.purchase_history, name='purchase_history'),
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('track/', views.track_order, name='track_order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('account/', views.account_view, name='account'),
    path('my-account/', views.my_account_view, name='my_account'),
    path('my-account/edit/', views.edit_profile_view, name='edit_profile'),
    path('my-account/delete/', views.delete_account_view, name='delete_account'),
    path('mpesa/stkpush/', views.initiate_payment, name='mpesa_stk_push'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('signup/seller/', views.seller_signup_view, name='seller_signup'),
    path('seller/<int:seller_id>/', views.seller_profile_public, name='seller_profile_public'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('api/pickup-stations/', api_utils.get_pickup_stations, name='api_pickup_stations'),
    # Footer Pages
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('faq/', views.faq, name='faq'),
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
]