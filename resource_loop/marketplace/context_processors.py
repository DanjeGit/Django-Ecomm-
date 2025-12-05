from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            count = 0
    else:
        # Support guest carts stored in session
        session_cart = request.session.get('cart', {})
        try:
            count = sum(int(qty) for qty in session_cart.values())
        except Exception:
            count = 0
    return {'cart_item_count': count}
