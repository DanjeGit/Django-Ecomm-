from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search_results, name='search'),
    path('item/<slug:slug>/', views.item_detail, name='item_detail'),
    path('loop2/', views.loop2_demo, name='loop2_demo'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/status/', views.payment_status, name='payment_status'),
    path('history/', views.purchase_history, name='purchase_history'),
    path('account/', views.account_view, name='account'),
    path('my-account/', views.my_account_view, name='my_account'),
    path('my-account/edit/', views.edit_profile_view, name='edit_profile'),
    path('my-account/delete/', views.delete_account_view, name='delete_account'),
    path('mpesa/stkpush/', views.initiate_payment, name='mpesa_stk_push'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
]