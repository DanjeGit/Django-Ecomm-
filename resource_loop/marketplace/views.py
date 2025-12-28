from requests import request
from .forms import UserForm, BuyerProfileForm, SellerProfileForm, SellerProfileForm
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
from django.core.mail import send_mail
from mpesa.utils import stk_push
import json
import random
import time
import uuid
from .models import OTP
from .locations import KENYA_LOCATIONS
from django.template.loader import render_to_string
from django.utils import timezone

def calculate_shipping_fee(seller_county, buyer_county):
    """
    Calculate shipping fee based on location.
    Same county: KSh 200
    Different county: KSh 500
    Unknown: KSh 300
    """
    if not seller_county or not buyer_county:
        return 300
    
    if seller_county.lower().strip() == buyer_county.lower().strip():
        return 200
    else:
        return 500

def send_otp_email(user, otp):
    print(f"📧 Preparing to send OTP {otp} to {user.email}...")
    # Import here to avoid circular import or startup errors
    try:
        from .tasks import send_email_task
        # Use Celery task
        message = f'Your verification code is: {otp}\n\nThe code will expire in 15 minutes.'
        send_email_task.delay(
            'Verify your Resource Loop Account',
            message,
            [user.email]
        )
    except ImportError:
        # Fallback if Celery is not set up
        from django.core.mail import send_mail
        send_mail(
            'Verify your Resource Loop Account',
            f'Your verification code is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )

def verify_email_view(request):
    if request.method == 'POST':
        otp_code = request.POST.get('otp')
        user_id = request.session.get('verification_user_id')
        
        try:
            user = User.objects.get(id=user_id)
            # Check DB for valid OTP
            otp_obj = OTP.objects.filter(user=user, code=otp_code, is_used=False).order_by('-created_at').first()
            
            if otp_obj and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                
                user.is_active = True
                user.save()
                
                # Clear session data
                if 'verification_user_id' in request.session: del request.session['verification_user_id']
                is_login = request.session.pop('is_login_verification', False)
                
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                if is_login:
                    messages.success(request, f"Welcome back, {user.username}!")
                else:
                    messages.success(request, f"Email verified! Welcome, {user.username}!")
                
                if user.is_superuser:
                    return redirect('/admin/')
                # If user has a seller profile, prefer seller dashboard
                if hasattr(user, 'sellerprofile'):
                    return redirect('seller_dashboard')
                return redirect('index')
            else:
                return render(request, 'registration/verify_email.html', {'error_message': 'Invalid or expired OTP.'})
                
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('signup')
            
    return render(request, 'registration/verify_email.html')

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
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('user_dashboard')
    return redirect('index')


@login_required
def user_dashboard(request):
    # Basic KPIs for buyers
    cart = getattr(request.user, 'cart', None)
    cart_items = cart.items.all() if cart else []
    total_cart_value = sum(ci.item.price * ci.quantity for ci in cart_items) if cart_items else 0

    # Account Summary
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    total_orders = orders.count()
    total_spent = sum(order.total_amount for order in orders)
    pending_orders = orders.filter(status__in=['placed', 'confirmed', 'processing']).count()

    # Recommended Items (Simple logic: Items not in cart, random selection)
    # In a real app, this would be based on purchase history
    all_items = list(WasteItem.objects.filter(stock_quantity__gt=0).exclude(seller__user=request.user))
    recommended_items = random.sample(all_items, min(len(all_items), 4))

    recent_items = WasteItem.objects.order_by('-created_at')[:8]
    categories = Category.objects.all()

    context = {
        'categories': categories,
        'cart_items': cart_items,
        'total_cart_value': total_cart_value,
        'recent_items': recent_items,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'pending_orders': pending_orders,
        'recommended_items': recommended_items,
        'recent_orders': orders[:5],
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
    recent_items = WasteItem.objects.order_by('-created_at')[:8]

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

def seller_profile_public(request, seller_id):
    seller = get_object_or_404(SellerProfile, id=seller_id)
    items = WasteItem.objects.filter(seller=seller, stock_quantity__gt=0)
    
    context = {
        'seller': seller,
        'items': items,
    }
    return render(request, 'marketplace/seller_profile_public.html', context)

@login_required
def add_listing(request):
    # Ensure user is a seller
    if not hasattr(request.user, 'sellerprofile'):
        messages.info(request, "You need to register as a seller to list items.")
        return redirect('seller_signup')

    categories = Category.objects.all()
    condition_choices = WasteItem.CONDITION_CHOICES

    if request.method == 'POST':
        seller_profile = request.user.sellerprofile

        category_id = request.POST.get('category')
        category = get_object_or_404(Category, id=category_id) if category_id else None
        
        county = request.POST.get('county')
        sub_county = request.POST.get('sub_county')
        # Construct location string from county/subcounty if provided, else fallback
        location = f"{sub_county}, {county}" if county and sub_county else request.POST.get('location', '')

        item = WasteItem.objects.create(
            seller=seller_profile,
            category=category,
            title=request.POST.get('title', 'Untitled'),
            description=request.POST.get('description', ''),
            specifications=request.POST.get('specifications', ''),
            price=request.POST.get('price') or 0,
            stock_quantity=request.POST.get('quantity') or 1,
            condition=request.POST.get('condition', 'used'),
            location=location,
            county=county,
            sub_county=sub_county,
            image=request.FILES.get('image')
        )
        return redirect('item_detail', slug=item.slug)

    context = {
        'categories': categories,
        'condition_choices': condition_choices,
        'kenya_locations_json': json.dumps(KENYA_LOCATIONS)
    }
    return render(request, 'marketplace/add_listing.html', context)

@require_POST
def add_to_cart(request, item_id):
    item = get_object_or_404(WasteItem, id=item_id)
    
    # Prevent self-purchase
    if request.user.is_authenticated and item.seller.user == request.user:
        messages.error(request, "You cannot buy your own item.")
        return redirect('item_detail', slug=item.slug)

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
    cart_items = cart.items.select_related('item', 'item__seller').all()
    
    # Check for self-owned items
    for cart_item in cart_items:
        if cart_item.item.seller.user == request.user:
            messages.error(request, f"You cannot purchase your own item: {cart_item.item.title}. Please remove it from your cart.")
            return redirect('cart')
    
    # Calculate Shipping
    shipping_fee = 0
    buyer_county = None
    if hasattr(request.user, 'buyerprofile'):
        buyer_county = request.user.buyerprofile.county
    
    processed_sellers = set()
    
    for cart_item in cart_items:
        seller = cart_item.item.seller
        if seller.id not in processed_sellers:
            fee = calculate_shipping_fee(seller.county, buyer_county)
            shipping_fee += fee
            processed_sellers.add(seller.id)

    subtotal = cart.get_total_price()
    grand_total = float(subtotal) + shipping_fee
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': grand_total,
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
    checkout_request_id = request.GET.get('checkout_request_id')
    if checkout_request_id:
        tx = Transaction.objects.filter(user=request.user, checkout_request_id=checkout_request_id).first()
        if tx:
            return JsonResponse({
                'pending': 1 if tx.state == 'pending' else 0,
                'confirmed': 1 if tx.state == 'confirmed' else 0,
                'cancelled': 1 if tx.state == 'cancelled' else 0,
            })
        # If not found, assume pending (it might be being created)
        return JsonResponse({'pending': 1, 'confirmed': 0, 'cancelled': 0})

    # Fallback: Check only recent transactions (last 15 mins) to avoid false positives from old history
    from django.utils import timezone
    from datetime import timedelta
    recent_time = timezone.now() - timedelta(minutes=15)
    
    pending = Transaction.objects.filter(user=request.user, state='pending', created_at__gte=recent_time).count()
    confirmed = Transaction.objects.filter(user=request.user, state='confirmed', created_at__gte=recent_time).count()
    cancelled = Transaction.objects.filter(user=request.user, state='cancelled', created_at__gte=recent_time).count()
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
        
        # Check if user already exists but is inactive (unverified)
        email = request.POST.get('email')
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user and not existing_user.is_active:
            # Resend OTP flow
            # Update password if provided? For now, just resend OTP
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.create(user=existing_user, code=otp_code)
            request.session['verification_user_id'] = existing_user.id
            
            try:
                send_otp_email(existing_user, otp_code)
                messages.info(request, f"Account exists but unverified. New code sent to {existing_user.email}")
                return redirect('verify_email')
            except Exception as e:
                print(f"Error sending OTP: {e}")
                return redirect('verify_email')

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            # Auto-generate username from email
            user.username = user.email
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.create(user=user, code=otp_code)
            
            # Store user ID in session for verification page
            request.session['verification_user_id'] = user.id
            
            # Deactivate user until verified
            user.is_active = False
            user.save()
            
            # Send Email
            try:
                send_otp_email(user, otp_code)
                messages.info(request, f"Verification code sent to {user.email}")
                return redirect('verify_email')
            except Exception as e:
                # Log error but don't crash, user can request resend
                print(f"Error sending OTP: {e}")
                return redirect('verify_email')
        else:
            messages.error(request, "There was an error with your signup. Please check the details you provided.")
    else:
        user_form = UserForm()
        profile_form = BuyerProfileForm()
        
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'login_form': AuthenticationForm(),
        'kenya_locations_json': json.dumps(KENYA_LOCATIONS)
    }
    return render(request, 'registration/login_signup.html', context)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.create(user=user, code=otp_code)
            
            # Store user ID in session for verification
            request.session['verification_user_id'] = user.id
            request.session['is_login_verification'] = True

            # Send Email
            try:
                send_otp_email(user, otp_code)
                messages.info(request, f"Verification code sent to {user.email}")
                return redirect('verify_email')
            except Exception as e:
                print(f"Error sending OTP: {e}")
                messages.error(request, "Error sending verification code.")
                return redirect('signup')
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
        'profile_form': profile_form,
        'kenya_locations_json': json.dumps(KENYA_LOCATIONS)
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


def send_seller_notifications(order):
    """
    Groups order items by seller and sends notifications (Email/SMS).
    """                                                                                         
    seller_items = {}
    
    # Group items by seller
    for order_item in order.items.all():
        if order_item.item and order_item.item.seller:
            seller = order_item.item.seller
            if seller not in seller_items:
                seller_items[seller] = []
            seller_items[seller].append(order_item)
    
    # Send notifications
    for seller, items in seller_items.items():
        # Prepare message
        item_list = "\n".join([f"- {i.item.title} (x{i.quantity})" for i in items])
        total_value = sum(i.price * i.quantity for i in items)
        
        subject = f"New Order Received! (Order #{order.id})"
        message = (
            f"Hello {seller.business_name},\n\n"
            f"You have received a new order for the following items:\n"
            f"{item_list}\n\n"
            f"Total Value: KES {total_value}\n"
            f"Please login to your dashboard to process this order.\n\n"
            f"Regards,\nResource Loop Team"
        )
        
        # 1. Send Email (Async)
        if seller.user.email:
            try:
                from .tasks import send_email_task
                # Render HTML email
                context = {
                    'seller': seller,
                    'order': order,
                    'items': items,
                    'total_value': total_value,
                    'domain': f"http://{settings.SITE_DOMAIN}" if not settings.SITE_DOMAIN.startswith('http') else settings.SITE_DOMAIN,
                    'year': timezone.now().year
                }
                html_message = render_to_string('emails/seller_order_notification.html', context)
                send_email_task.delay(subject, message, [seller.user.email], html_message=html_message)
            except ImportError:
                pass # Or fallback to sync send_mail
        
        # 2. Create In-App Notification (Async)
        from .tasks import create_notification_task
        create_notification_task.delay(
            seller.user.id,
            "New Order Received",
            f"You have a new order #{order.id} worth KES {total_value}",
            link=f"/orders/{order.id}/"
        )
        
        # 3. Send SMS (Simulation)
        phone = seller.payment_number
        if phone:
            print(f"📱 [SMS SIMULATION] To: {phone}")
            print(f"   Message: You have a new order! Check your dashboard. Items: {len(items)}")


def send_buyer_order_confirmation(order):
    """
    Sends an order confirmation email to the buyer.
    """
    if not order.user.email:
        return

    subject = f"Order Confirmation - Order #{order.id}"
    
    item_list = ""
    for item in order.items.all():
        item_list += f"- {item.item.title} (x{item.quantity}) @ KES {item.price}\n"
    
    message = (
        f"Hello {order.user.username},\n\n"
        f"Thank you for your order! Here are the details:\n\n"
        f"{item_list}\n"
        f"Total Amount: KES {order.total_amount}\n\n"
        f"We will notify you when your items are on their way.\n\n"
        f"Regards,\n\nResource Loop Team"
    )
    
    # Async Email
    try:
        from .tasks import send_email_task
        # Render HTML email
        context = {
            'order': order,
            'items': order.items.all(),
            'domain': f"http://{settings.SITE_DOMAIN}" if not settings.SITE_DOMAIN.startswith('http') else settings.SITE_DOMAIN,
            'year': timezone.now().year
        }
        html_message = render_to_string('emails/buyer_order_confirmation.html', context)
        send_email_task.delay(subject, message, [order.user.email], html_message=html_message)
    except ImportError:
        pass

    # Async Notification
    from .tasks import create_notification_task
    create_notification_task.delay(
        order.user.id,
        "Order Confirmed",
        f"Your order #{order.id} has been confirmed.",
        link=f"/orders/{order.id}/"
    )

@csrf_exempt
def mpesa_callback(request):
    """M-Pesa callback endpoint - Offloaded to Celery/Redis"""
    if request.method == "POST":
        try:
            callback_data = json.loads(request.body)
            
            print("========== M-PESA CALLBACK RECEIVED (Queuing Task) ==========")
            
            # Offload processing to Celery Task (Redis)
            from .tasks import process_mpesa_callback_task
            process_mpesa_callback_task.delay(callback_data)

            # Return 200 OK immediately to Safaricom
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback received and queued"})
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def seller_dashboard(request):
    # Ensure user has a seller profile
    seller_profile, created = SellerProfile.objects.get_or_create(user=request.user, defaults={'business_name': request.user.username})
    
    # Get all items listed by this seller
    my_listings = WasteItem.objects.filter(seller=seller_profile).order_by('-created_at')
    
    # Calculate stats
    active_listings_count = my_listings.filter(stock_quantity__gt=0).count()
    
    # Find order items that correspond to this seller's products
    # We look for OrderItems where the item's seller is the current user's profile
    # and the order status is 'confirmed', 'placed', 'processing', 'shipped', or 'delivered'
    sold_items = OrderItem.objects.filter(
        item__seller=seller_profile,
        order__status__in=['confirmed', 'placed', 'processing', 'shipped', 'delivered']
    ).select_related('order', 'item').order_by('-order__created_at')
    
    items_sold_count = sum(item.quantity for item in sold_items)
    total_sales = sum(item.price * item.quantity for item in sold_items)
    
    context = {
        'seller_profile': seller_profile,
        'my_listings': my_listings,
        'active_listings_count': active_listings_count,
        'items_sold_count': items_sold_count,
        'total_sales': total_sales,
        'recent_sales': sold_items[:10], # Show last 10 sales
    }
    return render(request, 'marketplace/dashboard_seller.html', context)

def seller_signup_view(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, prefix='user')
        buyer_profile_form = BuyerProfileForm(request.POST, prefix='buyer')
        seller_profile_form = SellerProfileForm(request.POST, prefix='seller')
        
        if user_form.is_valid() and buyer_profile_form.is_valid() and seller_profile_form.is_valid():
            user = user_form.save(commit=False)
            # Auto-generate username from email
            user.username = user.email
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            
            # Create Buyer Profile (for contact info)
            buyer_profile = buyer_profile_form.save(commit=False)
            buyer_profile.user = user
            buyer_profile.save()
            
            # Create Seller Profile
            seller_profile = seller_profile_form.save(commit=False)
            seller_profile.user = user
            seller_profile.save()
            
            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.create(user=user, code=otp_code)
            
            # Store user ID in session
            request.session['verification_user_id'] = user.id
            
            # Deactivate user until verified
            user.is_active = False
            user.save()
            
            # Send Email
            try:
                send_otp_email(user, otp_code)
                messages.info(request, f"Verification code sent to {user.email}")
                return redirect('verify_email')
            except Exception as e:
                print(f"Error sending OTP: {e}")
                return redirect('verify_email')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserForm(prefix='user')
        buyer_profile_form = BuyerProfileForm(prefix='buyer')
        seller_profile_form = SellerProfileForm(prefix='seller')
        
    context = {
        'user_form': user_form,
        'buyer_profile_form': buyer_profile_form,
        'seller_profile_form': seller_profile_form,
        'is_seller_signup': True,
        'kenya_locations_json': json.dumps(KENYA_LOCATIONS)
    }
    return render(request, 'registration/seller_signup.html', context)

def track_order(request):
    order = None
    error = None
    query = request.GET.get('q', '').strip()
    
    if query:
        # 1. Try searching by Order UUID
        try:
            # Check if it looks like a UUID
            uuid_obj = uuid.UUID(query)
            order = Order.objects.filter(order_uuid=uuid_obj).first()
        except ValueError:
            pass
            
        # 2. If not found, try searching by M-Pesa Receipt Number
        if not order:
            transaction = Transaction.objects.filter(mpesa_receipt_number__iexact=query).first()
            if transaction and transaction.order:
                order = transaction.order
        
        # 3. If still not found, try searching by Order ID (if numeric)
        if not order and query.isdigit():
             order = Order.objects.filter(id=query).first()

        if not order:
            error = f"No order found with Tracking ID: {query}"

    return render(request, 'marketplace/track_order.html', {
        'order': order,
        'error': error,
        'query': query
    })

def about(request):
    return render(request, 'marketplace/about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Save to DB (if migration works later)
        try:
            from .models import ContactMessage
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
            messages.success(request, "Your message has been sent! We will get back to you soon.")
        except Exception:
            # Fallback if model doesn't exist yet
            messages.success(request, "Thank you for contacting us!")
            
        return redirect('contact')
    return render(request, 'marketplace/contact.html')

def privacy(request):
    return render(request, 'marketplace/privacy.html')

def terms(request):
    return render(request, 'marketplace/terms.html')

def faq(request):
    return render(request, 'marketplace/faq.html')

def newsletter_signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            try:
                from .models import NewsletterSubscriber
                NewsletterSubscriber.objects.get_or_create(email=email)
                messages.success(request, "Thanks for subscribing to our newsletter!")
            except Exception:
                messages.success(request, "Thanks for subscribing!")
    return redirect(request.META.get('HTTP_REFERER', 'index'))