from requests import request
from .forms import UserForm, BuyerProfileForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import WasteItem, Category, Cart, CartItem, BuyerProfile, SellerProfile
from .models import Transaction, Order, OrderItem
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Count
from django.conf import settings
from mpesa.utils import stk_push
import json

def index(request):
    categories = Category.objects.all()
    flash_sales = WasteItem.objects.filter(is_flash_sale=True, stock_quantity__gt=0)[:4]
    verified_picks = WasteItem.objects.filter(is_verified_seller=True).exclude(id__in=flash_sales)[:6]
    recent_items = WasteItem.objects.all().order_by('-created_at')[:30]

    context = {
        'categories': categories,
        'flash_sales': flash_sales,
        'verified_picks': verified_picks,
        'recent_items': recent_items,
    }
    return render(request, 'marketplace/index.html', context)

def search_results(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    
    items = WasteItem.objects.all()
    categories = Category.objects.all()

    if query:
        items = items.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )
    
    if category_slug:
        items = items.filter(category__slug=category_slug)

    paginator = Paginator(items, 12) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'items': page_obj,
        'categories': categories,
        'query': query
    }
    return render(request, 'marketplace/search.html', context)

def item_detail(request, slug):
    item = get_object_or_404(WasteItem, slug=slug)
    related_items = WasteItem.objects.filter(category=item.category).exclude(id=item.id)[:4]
    
    context = {
        'item': item,
        'related_items': related_items
    }
    return render(request, 'marketplace/detail.html', context)

def loop2_demo(request):
    categories = Category.objects.all()
    recent_items = WasteItem.objects.all().order_by('-created_at')[:12]
    context = {
        'categories': categories,
        'recent_items': recent_items,
    }
    # redirect to main index to avoid duplicate content
    return redirect('index')


def account_view(request):
    categories = Category.objects.all()
    # simple profile info - in future show user-specific data
    context = {'categories': categories}
    return render(request, 'marketplace/account.html', context)


def cart_view(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        context = {
            'cart': cart,
            'is_guest': False,
        }
    else:
        session_cart = request.session.get('cart', {})
        items = []
        total = 0
        for item_id, qty in session_cart.items():
            try:
                item = WasteItem.objects.get(id=int(item_id))
                qty_int = int(qty)
                items.append({'item': item, 'quantity': qty_int, 'total': float(item.price) * qty_int})
                total += float(item.price) * qty_int
            except WasteItem.DoesNotExist:
                continue
        context = {
            'session_cart_items': items,
            'session_cart_total': total,
            'is_guest': True,
        }
    return render(request, 'marketplace/cart.html', context)


def dashboard(request):
    # Legacy view; redirect based on role
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    elif request.user.is_authenticated:
        return redirect('user_dashboard')
    return redirect('index')


@login_required
def user_dashboard(request):
    # Basic KPIs for buyers
    cart = getattr(request.user, 'cart', None)
    cart_items = cart.items.all() if cart else []
    total_cart_value = sum(ci.item.price * ci.quantity for ci in cart_items) if cart_items else 0

    recent_items = WasteItem.objects.order_by('-created_at')[:8]
    categories = Category.objects.all()

    context = {
        'categories': categories,
        'cart_items': cart_items,
        'total_cart_value': total_cart_value,
        'recent_items': recent_items,
    }
    return render(request, 'marketplace/dashboard_user.html', context)


@login_required
def admin_dashboard(request):
    # Admin overview metrics
    total_users = User.objects.count()
    total_items = WasteItem.objects.count()
    total_categories = Category.objects.count()
    sellers = SellerProfile.objects.count()
    buyers = BuyerProfile.objects.count()

    top_categories = (
        Category.objects.annotate(item_count=Count('items'))
        .order_by('-item_count')[:5]
    )
    recent_items = WasteItem.objects.order_by('-created_at')[:10]

    context = {
        'total_users': total_users,
        'total_items': total_items,
        'total_categories': total_categories,
        'sellers': sellers,
        'buyers': buyers,
        'top_categories': top_categories,
        'recent_items': recent_items,
    }
    return render(request, 'marketplace/dashboard_admin.html', context)


@login_required
def add_listing(request):
    categories = Category.objects.all()
    condition_choices = WasteItem.CONDITION_CHOICES

    if request.method == 'POST':
        # Get or create a seller profile for the current user
        seller_profile, created = SellerProfile.objects.get_or_create(
            user=request.user,
            defaults={'business_name': request.user.username} # Default business name
        )

        category_id = request.POST.get('category')
        category = get_object_or_404(Category, id=category_id) if category_id else None

        item = WasteItem.objects.create(
            seller=seller_profile,
            category=category,
            title=request.POST.get('title', 'Untitled'),
            description=request.POST.get('description', ''),
            specifications=request.POST.get('specifications', ''),
            price=request.POST.get('price') or 0,
            stock_quantity=request.POST.get('quantity') or 1,
            condition=request.POST.get('condition', 'used'),
            location=request.POST.get('location', ''),
            image=request.FILES.get('image')
        )
        return redirect('item_detail', slug=item.slug)

    context = {
        'categories': categories,
        'condition_choices': condition_choices
    }
    return render(request, 'marketplace/add_listing.html', context)

@require_POST
def add_to_cart(request, item_id):
    item = get_object_or_404(WasteItem, id=item_id)
    quantity = int(request.POST.get('quantity', 1))
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
        cart_item.quantity = cart_item.quantity + quantity if not created else quantity
        cart_item.save()
    else:
        session_cart = request.session.get('cart', {})
        current_qty = int(session_cart.get(str(item_id), 0))
        session_cart[str(item_id)] = current_qty + quantity
        request.session['cart'] = session_cart
        request.session.modified = True
    return redirect('cart')

@require_POST
def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
    else:
        session_cart = request.session.get('cart', {})
        # For guests, item_id refers to WasteItem id
        session_cart.pop(str(item_id), None)
        request.session['cart'] = session_cart
        request.session.modified = True
    return redirect('cart')

@require_POST
def update_cart(request, item_id):
    quantity = request.POST.get('quantity')
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        if quantity and quantity.isdigit() and int(quantity) > 0:
            cart_item.quantity = int(quantity)
            cart_item.save()
    else:
        if quantity and quantity.isdigit() and int(quantity) > 0:
            session_cart = request.session.get('cart', {})
            # For guests, item_id refers to WasteItem id
            if str(item_id) in session_cart:
                session_cart[str(item_id)] = int(quantity)
                request.session['cart'] = session_cart
                request.session.modified = True
    return redirect('cart')

def checkout_view(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to proceed to checkout.")
        return redirect('login')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('item').all()
    total = cart.get_total_price()
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'marketplace/checkout.html', context)

@login_required
def purchase_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'transactions': transactions,
    }
    return render(request, 'marketplace/history.html', context)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'marketplace/orders_list.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'marketplace/order_detail.html', {'order': order})

@login_required
def payment_status(request):
    pending = Transaction.objects.filter(user=request.user, state='pending').count()
    confirmed = Transaction.objects.filter(user=request.user, state='confirmed').count()
    cancelled = Transaction.objects.filter(user=request.user, state='cancelled').count()
    return JsonResponse({
        'pending': pending,
        'confirmed': confirmed,
        'cancelled': cancelled,
    })

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        username_confirm = request.POST.get('username_confirm')
        if username_confirm == request.user.username:
            user = request.user
            logout(request)
            user.delete()
            return redirect('marketplace:index')
        else:
            error_message = "Username confirmation failed. Please try again."
            return render(request, 'marketplace/delete_account.html', {'error_message': error_message})
    return render(request, 'marketplace/delete_account.html')

def signup_view(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = BuyerProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            user = authenticate(request, username=user_form.cleaned_data['username'], password=user_form.cleaned_data['password'])
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome, {user.username}! Your account has been created successfully.")
                if user.is_superuser:
                    return redirect('/admin/')
                return redirect('index')
        else:
            messages.error(request, "There was an error with your signup. Please check the details you provided.")
    else:
        user_form = UserForm()
        profile_form = BuyerProfileForm()
        
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'login_form': AuthenticationForm()
    }
    return render(request, 'registration/login_signup.html', context)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    
    # Redirect to the signup page which also contains the login form
    return redirect('signup')

@login_required
def my_account_view(request):
    buyer_profile = None
    if hasattr(request.user, 'buyerprofile'):
        buyer_profile = request.user.buyerprofile
    context = {
        'buyer_profile': buyer_profile,
    }
    return render(request, 'marketplace/my_account.html', context)


@login_required
def edit_profile_view(request):
    # Use getattr to safely get the profile, defaulting to None
    profile = getattr(request.user, 'buyerprofile', None)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        # The BuyerProfileForm is instantiated with the existing profile if it exists
        profile_form = BuyerProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()

            # Save the profile form with commit=False to get an instance
            # without committing to the database yet.
            profile_instance = profile_form.save(commit=False)
            
            # CRITICAL FIX:
            # If the profile was None (i.e., it's a new profile), we must
            # assign the user to it before saving. If the profile already
            # existed, the instance is already linked to the user, so this
            # step is not needed and would cause the error.
            if profile is None:
                profile_instance.user = request.user
            
            # Now, save the instance. This will either UPDATE the existing
            # profile or INSERT the new one with the correct user_id.
            profile_instance.save()
            
            return redirect('my_account')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = BuyerProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'marketplace/edit_profile.html', context)


@csrf_exempt
def initiate_payment(request):
    if request.method == "POST":
        # 1. Prefer phone from form; fallback to profile if present
        form_phone = request.POST.get("phone_number")
        profile_phone = None
        try:
            profile_phone = request.user.buyerprofile.phone_number
        except AttributeError:
            profile_phone = None
        phone = form_phone or profile_phone

        # 2. Get the amount: prefer server-side cart total to avoid tampering
        amount = request.POST.get("amount")
        try:
            cart = Cart.objects.get(user=request.user)
            cart_total = cart.get_total_price()
            # If no amount provided or mismatch, use cart total
            if not amount or float(amount) != float(cart_total):
                amount = cart_total
        except Cart.DoesNotExist:
            return JsonResponse({"error": "Cart is empty"}, status=400)

        # 3. Validate inputs
        if not phone or not amount:
            return JsonResponse({"error": "Phone number is required. Please enter your M-Pesa phone."}, status=400)

        # Optionally persist provided phone if profile exists and is empty
        if form_phone and not profile_phone:
            try:
                bp = getattr(request.user, 'buyerprofile', None)
                if bp:
                    bp.phone_number = form_phone
                    bp.save(update_fields=['phone_number'])
            except Exception:
                pass

        # 4. Call the utility function
        # The logic is now safely inside utils.py so this view stays clean
        result = stk_push(amount, phone)

        # Create a single Order and OrderItems snapshot to avoid duplicates
        cart_items = cart.items.select_related('item').all()
        order = Order.objects.create(user=request.user, total_amount=cart.get_total_price(), status='payment_pending')
        for ci in cart_items:
            OrderItem.objects.create(order=order, item=ci.item, quantity=ci.quantity, price=ci.item.price)

        # Create one Transaction linked to the order with STK identifiers
        mpesa_name = request.user.get_full_name() or request.user.username
        # If STK push failed, cancel order and return error
        if result.get('error'):
            order.status = 'cancelled'
            order.save()
            return JsonResponse(result, status=result.get('status') or 400)

        checkout_id = result.get('CheckoutRequestID') or (result.get('data') or {}).get('CheckoutRequestID')
        merchant_id = result.get('MerchantRequestID') or (result.get('data') or {}).get('MerchantRequestID')
        # Guard: avoid duplicates if a pending transaction already exists for this order
        tx, created_tx = Transaction.objects.get_or_create(
            order=order,
            checkout_request_id=checkout_id,
            defaults={
                'user': request.user,
                'mpesa_name': mpesa_name,
                'phone_number': phone,
                'item': None,
                'amount': order.total_amount,
                'state': 'pending',
                'merchant_request_id': merchant_id,
            }
        )

        # 5. Check if utils returned an internal error
        if "error" in result:
            return JsonResponse(result, status=400)

        return JsonResponse(result)

    return JsonResponse({"error": "POST request required"}, status=405)


@csrf_exempt
def mpesa_callback(request):
    """M-Pesa callback endpoint"""
    if request.method == "POST":
        try:
            callback_data = json.loads(request.body)
            
            # Log the data to your console to verify it works
            print("========== M-PESA CALLBACK RECEIVED ==========")
            print(json.dumps(callback_data, indent=4)) 

            # Extract details for transaction recording
            body = callback_data.get('Body', {})
            stk_cb = body.get('stkCallback', {})
            result_code = stk_cb.get('ResultCode')
            checkout_request_id = stk_cb.get('CheckoutRequestID')
            metadata = stk_cb.get('CallbackMetadata', {})
            items = metadata.get('Item', []) if isinstance(metadata, dict) else []

            amount = None
            phone = None
            mpesa_name = ''
            # Parse typical M-Pesa callback metadata items
            for it in items:
                name = it.get('Name')
                val = it.get('Value')
                if name == 'Amount':
                    amount = val
                elif name in ('PhoneNumber', 'MSISDN'):
                    phone = str(val)
                elif name in ('FirstName', 'MiddleName', 'LastName'):
                    mpesa_name = (mpesa_name + ' ' + str(val)).strip()

            # Find user by phone in BuyerProfile
            user = None
            if phone:
                try:
                    bp = BuyerProfile.objects.get(phone_number=phone)
                    user = bp.user
                except BuyerProfile.DoesNotExist:
                    user = None

            # Update the single transaction and its order based on result
            if checkout_request_id:
                tx = Transaction.objects.filter(checkout_request_id=checkout_request_id).first()

                if tx:
                    if result_code == 0:
                        tx.state = 'confirmed'
                        tx.mpesa_name = mpesa_name or (user.get_full_name() if user else '')
                        tx.phone_number = phone or tx.phone_number
                        tx.save()
                        # Update order status to placed
                        if tx.order:
                            tx.order.status = 'placed'
                            tx.order.save()
                        # Clear cart after confirmation
                        try:
                            if user:
                                cart = Cart.objects.get(user=user)
                                cart.items.all().delete()
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

            return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback received"})
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)