from django.contrib import admin
from .models import Category, WasteItem, SellerProfile, BuyerProfile, Transaction, Order, OrderItem, ShippingConfiguration, PickupStation, ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'description', 'ip_address')
    readonly_fields = ('user', 'action', 'description', 'ip_address', 'timestamp')

    def has_add_permission(self, request):
        return False

@admin.register(PickupStation)
class PickupStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'county', 'sub_county')
    list_filter = ('county', 'sub_county')
    search_fields = ('name', 'county', 'sub_county')

@admin.register(ShippingConfiguration)
class ShippingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('same_county_fee', 'different_county_fee', 'standard_fee')
    # Prevent adding more than one configuration
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

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
    list_display = ('user', 'amount', 'state', 'mpesa_receipt_number', 'mpesa_name', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('user__username', 'mpesa_name', 'phone_number', 'mpesa_receipt_number', 'checkout_request_id')
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