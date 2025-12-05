from django.contrib import admin
from .models import Category, WasteItem, SellerProfile, BuyerProfile, Transaction, Order, OrderItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_class')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(WasteItem)
class WasteItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'seller', 'is_flash_sale', 'created_at')
    list_filter = ('category', 'is_flash_sale', 'condition')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'is_verified')
    search_fields = ('business_name', 'user__username')

@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'location')
    search_fields = ('user__username', 'phone_number')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'state', 'merchant_request_id', 'checkout_request_id', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('user__username', 'mpesa_name', 'phone_number', 'item__title', 'merchant_request_id', 'checkout_request_id')
    ordering = ('-created_at',)
    actions = ('mark_confirmed', 'mark_cancelled')

    @admin.action(description="Mark selected as Confirmed")
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(state='confirmed')
        self.message_user(request, f"Marked {updated} transactions as confirmed.")

    @admin.action(description="Mark selected as Cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(state='cancelled')
        self.message_user(request, f"Marked {updated} transactions as cancelled.")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_uuid', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'order_uuid', 'user__username')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item', 'quantity', 'price')
    search_fields = ('order__id', 'item__title')