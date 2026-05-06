import requests
import base64
import json
import random
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Sum, F

from decimal import Decimal
from collections import defaultdict
from io import BytesIO

from django import forms
from django.db.models import Sum, F, Q, Count
from django.utils.timezone import now as tz_now
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa

from .models import (
    Product, Category, ProductImage, CartItem, Order, OrderItem,
    SiteSettings, Brand, ProductView, UserActivity
)
from .forms import SignupForm
from django.core.paginator import Paginator
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.mail import send_mail

from django.http import JsonResponse # Import this!

from django.shortcuts import get_object_or_404, render
from django.db.models import F
from .models import Product
from datetime import datetime
import random

from django.utils import timezone
from django.db.models import Sum
from django.core.paginator import Paginator
from django.shortcuts import render
import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from .models import EmailOTP
from django.contrib.auth.models import User

from django.shortcuts import render
from django.utils import timezone
from django.db.models import F, ExpressionWrapper, DateTimeField, Sum
from django.core.paginator import Paginator
from datetime import timedelta
from .models import Product, Brand, CartItem # Ensure these are imported
from django.db.models import F, ExpressionWrapper, DateTimeField, Sum, Value, DurationField

def index_view(request):
    now = timezone.now()

    # 1. Base query with annotation
    active_products_query = Product.objects.annotate(
        expiry=ExpressionWrapper(
            F('discount_start_time') + (F('discount_duration_hours') * Value(timedelta(hours=1), output_field=DurationField())),
            output_field=DateTimeField()
        )
    )

    # ✅ FIX 1: Convert expired QuerySet to a list to avoid SQLite math errors
    try:
        expired_products = list(active_products_query.filter(
            discount_start_time__isnull=False,
            expiry__lt=now
        ).values_list('id', flat=True))

        if expired_products:
            Product.objects.filter(id__in=expired_products).update(
                discount=0, 
                discount_start_time=None, 
                discount_duration_hours=0
            )
    except Exception as e:
        print(f"Cleanup error: {e}")

    # 2. Sidebar data
    brands = Brand.objects.all()
    
    # ✅ FIX 2: Convert quick_sales to a list immediately
    # This executes the query HERE in the view, rather than letting the template 
    # trigger the crash at line 439.
    quick_sales = list(active_products_query.filter(
        discount__gt=0,
        stock__gt=0,
        discount_start_time__isnull=False,
        expiry__gt=now
    ).order_by('-discount')[:8])

    # 3. Featured Products
    all_featured = Product.objects.all().order_by('-id')
    paginator = Paginator(all_featured, 24)
    page_number = request.GET.get('page')
    featured_products = paginator.get_page(page_number)

    # 4. Cart Count
    cart_count = 0
    if request.user.is_authenticated:
        result = CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))
        cart_count = result['total'] or 0

    return render(request, 'index.html', {
        'brands': brands,
        'quick_sales': quick_sales,  # Now a safe Python list
        'featured_products': featured_products,
        'cart_count': cart_count
    })
def about(request):
    return render(request, 'about.html')
def products_view(request):
    products_list = Product.objects.all().order_by('-id')
    
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    brand_id = request.GET.get('brand')
    category_id = request.GET.get('category')

    if brand_id and brand_id.isdigit():
        products_list = products_list.filter(brand_id=brand_id)
        brand_id = int(brand_id)
    if category_id and category_id.isdigit():
        products_list = products_list.filter(category_id=category_id)
        category_id = int(category_id)

    # PAGINATION LOGIC: 30 items per page
    paginator = Paginator(products_list, 30)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'products': products, # This is now a Page object
        'categories': categories,
        'brands': brands,
        'selected_brand': brand_id,
        'selected_category': category_id,
    }
    return render(request, 'products.html', context)

@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')

    total = sum(item.quantity * item.product.final_price for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)

    if request.GET.get('ajax'):
        items = []
        for item in cart_items:
            product = item.product
            first_image = product.images.first()
            if first_image:
                image_url = first_image.image.url
            elif product.image:
                image_url = product.image.url
            else:
                image_url = '/static/images/default.png'
            items.append({
                'id': item.id,
                'price': float(product.final_price),
                'name': product.name,
                'quantity': item.quantity,
                'image': image_url,
            })
        return JsonResponse({
            'items': items,
            'total': float(total),
            'cart_count': cart_count,
        })

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count
    })


def create_default_categories():
    categories = [
        "Kitchen Appliances",
        "Phones & Tablets",
        "Computers & Laptops",
        "TVs & Entertainment",
        "Audio Devices",
        "Networking Equipment",
        "Home Appliances",
        "Power & Electrical Accessories",
        "Cables & Connectors",
        "Batteries & Power Banks",
        "Lighting Equipment",
        "CCTV & Security Systems",
        "Gaming Accessories",
        "Smart Home Devices",
        "Wearables",
        "Office Electronics",
        "Printers & Scanners",
        "Computer Accessories",
        "Mobile Accessories",
        "Solar & Energy Solutions",
        "Extension Cables & Adaptors",
        "Chargers & Adapters",
        "Fans & Cooling Systems",
        "Irons & Heating Appliances",
        "Fridges & Freezers",
        "Cookers & Ovens",
        "Blenders & Mixers",
        "Microwaves",
        "Electric Kettles"
    ]

    for cat in categories:
        Category.objects.get_or_create(name=cat)


    
@staff_member_required
@staff_member_required
def customers(request):
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')

    return render(request, 'customers.html', {
        'orders': orders
    })


def products_by_category_view(request, brand_id=None, category_id=None):
    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    current_brand_id = brand_id
    current_cat_id = category_id

    # Filter by Brand if ID is provided
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    # Filter by Category if ID is provided
    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'current_brand_id': current_brand_id,
        'current_cat_id': current_cat_id,
        # add cart_count here as well if needed
    }
    return render(request, 'products.html', context)
def product_detail(request, pk):
    product = get_object_or_404(Product, id=pk)
    if product.stock <=0:
        messages.error(request,"This product is currently out of stock.")
        return redirect('products')

    now_time= datetime.now()
    seed_value = int(f"{pk}{now_time.day}{now_time.hour // 12}")
    random.seed(seed_value)
    """
    Displays product detail including reviews, recommendations, and dynamic pricing.
    """
    # Step 1: Fetch the product from the database
    product = get_object_or_404(Product, id=pk)
    
    # Step 2: Generate fake social proof (ratings, stars, etc.) for product
    now_time = datetime.now()
    seed_value = int(f"{pk}{now_time.day}{now_time.hour // 12}")
    random.seed(seed_value)
    fake_rating = round(random.uniform(4.4, 5.0), 1)
    
    social_proof = {
        'rating': fake_rating,
        'count': random.randint(28, 145),
        'stars': '★' * int(fake_rating) + '☆' * (5 - int(fake_rating))
    }

    # Step 3: Update the product view count (for analytics)
    Product.objects.filter(id=pk).update(views=F('views') + 1)

    # Step 4: Handle user activity tracking if logged in
    if request.user.is_authenticated:
        # Track activity logic (optional for this view)
        pass

    # Step 5: Fetch product recommendations based on category
    recommended = Product.objects.filter(category=product.category).exclude(id=product.id).order_by('?')[:10]

    # Step 6: Pass all data to the template for rendering
    return render(request, 'product_detail.html', {
        'product': product,
        'social_proof': social_proof,
        'recommended_products': recommended,
        'discount_expiry': product.discount_expiry.isoformat() if product.discount_expiry else None,
    })

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    

    if not product.stock or product.stock <= 0:
        return JsonResponse({"success": False, "message": "Product is out of stock."})

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user, product=product, defaults={'quantity': 1}
    )

    if not created:
        if cart_item.quantity + 1 > product.stock:
            return JsonResponse({"success": False, "message": "Not enough stock available."})
        cart_item.quantity += 1
        cart_item.save()

    cart_count = CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))['total'] or 0

    return JsonResponse({
        "success": True,
        "cart_count": cart_count
    })

def products_by_brand(request, brand_id):
    products = Product.objects.filter(brand__id=brand_id)
    brands = Brand.objects.all()
    categories = Category.objects.all()

    return render(request, 'products.html', {  # ✅ use SAME template
        'products': products,
        'brands': brands,
        'categories': categories
    })

@login_required
@staff_member_required

def add_product(request):
    create_default_categories()
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        discount_val = request.POST.get("discount")
        stock = request.POST.get("stock")
        brand_id = request.POST.get("brand")
        category_id = request.POST.get("category")
        new_category = request.POST.get("new_category")
        offer_days = request.POST.get('offer_days')  
        specifications = request.POST.get("specifications")
        short_desc = request.POST.get('short_description')
        duration_val = request.POST.get("discount_duration_hours")

        if not brand_id:
            messages.error(request, "Please select a brand.")
            return redirect("add_product")

        brand = Brand.objects.get(id=brand_id)

        if new_category:
            category, created = Category.objects.get_or_create(name=new_category)
        else:
            if not category_id:
                messages.error(request, "Please select or create a category.")
                return redirect("add_product")
            category = Category.objects.get(id=category_id)

        # Create product
        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            category=category,
            brand=brand,
            short_description=short_desc,
            specifications=specifications
        )

        # Convert safely
        discount = float(discount_val) if discount_val else 0
        duration = int(duration_val) if duration_val and duration_val.isdigit() else 0

        product.discount = discount
        product.discount_duration_hours = duration

        # AUTO-START SALE
        if discount > 0 and duration > 0:
            product.discount_start_time = timezone.now()

        product.save()

        # Handle Images
        images = request.FILES.getlist('images')
        for img in images:
            ProductImage.objects.create(product=product, image=img)

        messages.success(request, f"{product.name} added successfully!")
        
        # --- REDIRECT BACK TO THE SAME PAGE ---
        return redirect("add_product")

    return render(request, "add_product.html", {
        "categories": categories,
        "brands": brands
    })

@login_required
@login_required
def increase_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.quantity += 1
    item.save()
    return JsonResponse({"success": True, "quantity": item.quantity})


@login_required
def decrease_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        return JsonResponse({"success": True, "quantity": item.quantity})
    else:
        item.delete()
        return JsonResponse({"success": True, "quantity": 0, "removed": True})


@login_required
def remove_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({"success": True})


import traceback
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.core.mail import send_mail
def check(request):
    # --- FETCH DATA ---
    config, _ = SiteSettings.objects.get_or_create(id=1)

    direct_product_id = request.session.get('direct_product')

    # --- HANDLE DIRECT CHECKOUT ---
    if direct_product_id:
        product = get_object_or_404(Product, id=direct_product_id)

        class SingleItem:
            def __init__(self, product):
                self.product = product
                self.quantity = 1

        cart_items = [SingleItem(product)]
        is_direct = True
    else:
        cart_items = CartItem.objects.filter(user=request.user)
        is_direct = False

    # --- EMPTY CART CHECK ---
    if not is_direct and not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')

    # --- STOCK VALIDATION ---
    for item in cart_items:
        if item.product.stock <= 0:
            messages.error(request, f"{item.product.name} is OUT OF STOCK.")
            return redirect("view_cart")

        if item.quantity > item.product.stock:
            messages.error(
                request,
                f"Only {item.product.stock} units available for {item.product.name}."
            )
            return redirect("view_cart")

    # --- CALCULATIONS ---
    subtotal = sum(item.quantity * item.product.final_price for item in cart_items)

    product_shipping_fees = [item.product.shipping_fee for item in cart_items]
    max_cart_shipping = max(product_shipping_fees) if product_shipping_fees else Decimal('0.00')

    # --- POST: PROCESS ORDER ---
    if request.method == "POST":
        try:
            with transaction.atomic():

                name = request.POST.get("name")
                email = request.POST.get("email")
                phone = request.POST.get("phone")
                address = request.POST.get("address")
                region = request.POST.get("region")
                payment_method = request.POST.get("payment_method")

                # --- SHIPPING ---
                shipping_fee = max_cart_shipping if region == "outside" else config.shipping_fee_nairobi
                final_total = subtotal + shipping_fee

                # --- PHONE FORMAT ---
                clean_phone = phone.strip().replace("+", "")
                if clean_phone.startswith("0"):
                    clean_phone = "254" + clean_phone[1:]
                elif not clean_phone.startswith("254"):
                    clean_phone = "254" + clean_phone

                # --- LOCATION ---
                location_area = (
                    request.POST.get("nairobi_area")
                    if region == "nairobi"
                    else request.POST.get("outside_town")
                )
                full_destination = f"{location_area} - {address}"

                # --- CREATE ORDER ---
                order = Order.objects.create(
                    user=request.user,
                    name=name,
                    email=email,
                    phone=clean_phone,
                    destination=full_destination,
                    total=final_total,
                    shipping_fee=shipping_fee,
                    region=region,
                    status="Pending",
                    payment_status="Awaiting Payment",
                    payment_method=payment_method
                )

                # --- CREATE ORDER ITEMS ---
                items_summary = ""

                for item in cart_items:
                    product = item.product

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.final_price
                    )

                    # 🔥 REDUCE STOCK
                    product.stock -= item.quantity
                    product.save()

                    items_summary += f"- {product.name} (x{item.quantity}) @ KES {product.final_price}\n"

                # --- RECEIPT URL ---
                protocol = 'https' if request.is_secure() else 'http'
                domain = request.get_host()
                receipt_url = f"{protocol}://{domain}{reverse('download_receipt', args=[order.id])}"

                # --- SEND EMAIL ---
                subject = f"Order Confirmed - Gadget Soko #{order.id}"
                message = (
                    f"Hello {name},\n\n"
                    f"Your order #{order.id} has been received.\n\n"
                    f"Items:\n{items_summary}\n"
                    f"Shipping: KES {shipping_fee}\n"
                    f"Total: KES {final_total}\n\n"
                    f"Download Receipt:\n{receipt_url}\n\n"
                    f"Thank you for shopping with us!"
                )

                try:
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [email],
                        fail_silently=False
                    )
                except Exception as e:
                    print("EMAIL ERROR:", str(e))
                    traceback.print_exc()

                # --- PAYMENT ---
                if payment_method == "mpesa":
                    try:
                        response = lipa_na_mpesa(
                            phone_number=clean_phone,
                            amount=int(final_total),
                            account_ref=f"GSK{order.id}",
                            transaction_desc="Gadget Purchase"
                        )

                        if response.get('ResponseCode') == '0':
                            order.checkout_request_id = response.get('CheckoutRequestID')
                            order.status = 'STK_Sent'
                            order.save()

                    except Exception as e:
                        print("MPESA ERROR:", str(e))
                        messages.error(request, "M-Pesa request failed.")

                elif payment_method == "pod":
                    order.payment_status = "Pay on Delivery"
                    order.status = "Confirmed"
                    order.save()

                # --- CLEAR CART OR SESSION ---
                if is_direct:
                    request.session.pop('direct_product', None)
                else:
                    cart_items.delete()

                messages.success(request, f"Order #{order.id} placed successfully!")
                return redirect('payment_instructions', order_id=order.id)

        except Exception as e:
            print("CHECKOUT ERROR:", str(e))
            traceback.print_exc()
            messages.error(request, "Something went wrong.")
            return redirect('view_cart')

    # --- GET REQUEST ---
    context = {
        'subtotal': subtotal,
        'cart_items': cart_items,
        'config': config,
        'max_shipping': max_cart_shipping,
        'shipping_nairobi': config.shipping_fee_nairobi
    }

    return render(request, 'check.html', context)


def payment_instructions(request, order_id):
    # Fetch the order and ensure it belongs to the logged-in user
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    return render(request, 'payment_instructions.html', {
        'order': order,
        'method': order.payment_status # Or order.payment_method depending on your model
    })


def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET
        )
    )
    try:
        data = response.json()
        return data.get('access_token')
    except ValueError:
        print("Token response error:", response.text)  # log raw response for debugging
        return None
# --- 1. USER SIGNUP (Create Account) ---
import random
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import SignupOTP


def usersignup_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validations
        if not username or not email or not password1:
            messages.error(request, "All fields are required.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "An account with that email already exists.")
        else:
            otp = str(random.randint(100000, 999999))

            # store OTP + user details temporarily
            SignupOTP.objects.update_or_create(
                email=email,
                defaults={
                    "username": username,
                    "password": password1,
                    "otp": otp
                }
            )

            # send OTP
            send_mail(
                subject="Gadget Soko OTP Verification",
                message=f"Your OTP code is {otp}. It expires in 10 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False
            )

            # store email in session
            request.session["signup_email"] = email

            messages.success(request, "OTP has been sent to your email. Please verify.")
            return redirect("verify_signup_otp")

    return render(request, 'signup.html')

    return render(request, 'signup.html')

from django.contrib.auth import login


def verify_signup_otp(request):
    email = request.session.get("signup_email")

    if not email:
        messages.error(request, "Session expired. Please signup again.")
        return redirect("signup")

    try:
        otp_obj = SignupOTP.objects.get(email=email)
    except SignupOTP.DoesNotExist:
        messages.error(request, "OTP not found. Please signup again.")
        return redirect("signup")

    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, "OTP expired. Please signup again.")
            return redirect("signup")

        if otp_input != otp_obj.otp:
            messages.error(request, "Invalid OTP. Try again.")
            return redirect("verify_signup_otp")

        # create user after OTP success
        user = User.objects.create_user(
            username=otp_obj.username,
            email=otp_obj.email,
            password=otp_obj.password
        )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        otp_obj.delete()
        request.session.pop("signup_email", None)

        messages.success(request, f"Account created successfully! Welcome {user.username} 🎉")
        return redirect("index")

    return render(request, "verify_otp.html", {"email": email})
# --- 2. USER LOGIN (Sign In) ---
def userlog_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == "POST":
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username_or_email or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'login.html')

        # First, try authenticating with the username
        user = authenticate(request, username=username_or_email, password=password)

        # If username fails, try authenticating with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}! 👋")
            return redirect(request.GET.get('next', 'index'))
        else:
            messages.error(request, "Incorrect username/email or password.")
    
    return render(request, 'login.html')


# --- 3. ADMIN SECRET LOGIN ---
def secretkey_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff: # ✅ Checks if user has admin access
                login(request, user)
                messages.success(request, f"Access Granted. Welcome, Admin {user.username}.")
                return redirect('dashboard')
            else:
                messages.error(request, "Unauthorized access. Staff only.")
                return redirect('index')
        else:
            messages.error(request, "Invalid admin credentials.")
            return redirect('secretkey')

    return render(request, 'admin_login_template.html') # Use a specific admin template
    
  

    


def search_view(request):
    query = request.GET.get('q')
    results = []
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(brand__name__icontains=query) |
            Q(specifications__icontains=query)
        ).distinct()
    
    return render(request, 'search_results.html', {'results': results, 'query': query})




def logout_view(request):
    logout(request)
    return redirect('index')

@staff_member_required
def dashboard_view(request):
    # Basic stats
    products_count = Product.objects.count()
    orders_count = Order.objects.count()
    users_count = User.objects.count()
    revenue = Order.objects.aggregate(total_revenue=Sum('total'))['total_revenue'] or 0

    # Recent orders
    recent_orders = Order.objects.order_by('-id')[:5]

    # Customer activity logs (last 20)
    activity_logs = UserActivity.objects.select_related('user', 'product').order_by('-timestamp')[:20]

    for log in activity_logs:
        # Fetch last order of the user
        latest_order = Order.objects.filter(user=log.user).order_by('-created_at').first()
        log.last_order_status = latest_order.status if latest_order else "Browsing Only"

    # Revenue per month (last 6 months)
    today = datetime.today()
    revenue_data = defaultdict(int)
    for i in range(6, 0, -1):
        month = (today.month - i) % 12 or 12
        orders_in_month = Order.objects.filter(created_at__month=month)
        month_name = datetime(1900, month, 1).strftime('%b')
        revenue_data[month_name] = sum(o.total for o in orders_in_month if o.total)

    revenue_labels = list(revenue_data.keys())
    revenue_values = list(revenue_data.values())

    # Top products by total sold
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')  # Adjust related_name if needed
    ).order_by('-total_sold')[:5]

    top_products_labels = [p.name for p in top_products]
    top_products_values = [p.total_sold or 0 for p in top_products]

    context = {
        "products_count": products_count,
        "orders_count": orders_count,
        "users_count": users_count,
        "revenue": revenue,
        "recent_orders": recent_orders,
        "revenue_labels": revenue_labels,
        "revenue_values": revenue_values,
        "top_products_labels": top_products_labels,
        "top_products_values": top_products_values,
        "customer_activity": activity_logs,
        "products": Product.objects.all(),
    }

    return render(request, "dashboard.html", context)



@staff_member_required
def activity_view(request):
    # Fetch last 20 activity logs
    activity_logs = UserActivity.objects.select_related('user', 'product').order_by('-timestamp')[:20]

    for log in activity_logs:
        # Find the latest order of each user
        latest_order = Order.objects.filter(user=log.user).order_by('-created_at').first()
        log.last_order_status = latest_order.status if latest_order else "Browsing Only"

    context = {
        "customer_activity": activity_logs,
    }
    return render(request, "activity.html", context)







@staff_member_required
def analytics_view(request):
    # 1. Revenue by Date (Changed 'total_price' to 'total')
    revenue_data = Order.objects.values('created_at__date').annotate(
        total_daily=Sum('total')
    ).order_by('created_at__date')
    
    revenue_labels = [str(item['created_at__date']) for item in revenue_data]
    revenue_values = [float(item['total_daily'] or 0) for item in revenue_data]

    # 2. Top Products (Assuming OrderItem has 'quantity' and 'product')
    # Note: If 'product' is a ForeignKey, use 'product__name'
    product_data = OrderItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]
    
    top_products_labels = [item['product__name'] for item in product_data]
    top_products_values = [int(item['total_sold'] or 0) for item in product_data]

    context = {
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_values': json.dumps(revenue_values),
        'top_products_labels': json.dumps(top_products_labels),
        'top_products_values': json.dumps(top_products_values),
    }
    return render(request, 'analytics.html', context)
@staff_member_required
def settings_view(request):
    # You can pass forms here if needed
    context = {}
    return render(request, "settings.html", context)
@staff_member_required
def manage_products(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'manage_products.html', {'products': products})


@staff_member_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('manage_products')


# ================= ORDERS =================
@staff_member_required
def manage_orders(request):
    orders = Order.objects.all().order_by('-id')
    return render(request, 'manage_orders.html', {'orders': orders})


@staff_member_required
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = request.POST.get('status')
    order.save()
    return redirect('manage_orders')
def lipa_na_mpesa(phone_number, amount, account_ref, transaction_desc):
    token = get_mpesa_access_token()

    if not token:
        return {
            "error": "Failed to generate access token"
        }

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode("utf-8")

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_ref,
        "TransactionDesc": transaction_desc
    }

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print("MPESA STK Push Status Code:", response.status_code)
    print("MPESA STK Push Raw Response:", response.text)

    try:
        return response.json()
    except ValueError as e:
        print("JSON decode error:", e)
        return {
            "error": "Invalid JSON response from MPESA STK Push",
            "status_code": response.status_code,
            "response_text": response.text
        }
# ================= CALLBACK =================




@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        stk_callback = data['Body']['stkCallback']
        result_code = stk_callback['ResultCode']
        checkout_request_id = stk_callback['CheckoutRequestID']

        if result_code == 0:
            # Payment Successful
            # Metadata contains the M-Pesa Receipt Number and Phone
            metadata = stk_callback['CallbackMetadata']['Item']
            mpesa_receipt = next(item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber')
            
            # Find the order using the CheckoutID we saved during the push
            try:
                order = Order.objects.get(mpesa_checkout_id=checkout_request_id)
                order.status = 'Paid'
                order.mpesa_receipt = mpesa_receipt
                order.save()
            except Order.DoesNotExist:
                pass 

def initiate_payment(request, order_id):
    order = Order.objects.get(id=order_id)
    # Call your STK push utility
    response = initiate_stk_push(order.phone, order.total_price, order.id)
    
    if response.get('ResponseCode') == '0':
        # SAVE the CheckoutRequestID to the order
        order.mpesa_checkout_id = response['CheckoutRequestID']
        order.save()
        return JsonResponse({'status': 'sent', 'message': 'Check your phone for the PIN prompt!'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to trigger M-Pesa'})
def register_mpesa_urls(request):
    access_token = get_mpesa_access_token()

    api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "ShortCode": settings.MPESA_SHORTCODE,
        "ResponseType": "Completed",
        "ConfirmationURL": "https://eloy-headstrong-eventfully.ngrok-free.dev/payment_callback/",
        "ValidationURL": "https://eloy-headstrong-eventfully.ngrok-free.dev/payment_callback/",
    }

    response = requests.post(api_url, json=payload, headers=headers)

    return JsonResponse(response.json())

    
    response = requests.post(api_url, json=payload, headers=headers)

    return JsonResponse(response.json())


@staff_member_required
def update_price(request, pk):
    if request.method == "POST":
        product = get_object_or_404(Product, id=pk)
        new_price = request.POST.get("price")

        product.price = new_price
        product.save()

    return redirect('manage_products')


from django.shortcuts import get_object_or_404, redirect
from .models import Product

@staff_member_required

def mark_out_of_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.stock = 0
    product.save()
    return redirect('manage_products')


def live_search(request):
    query = request.GET.get('q', '').strip()  # get the search query
    if query:
        # Search in name OR specifications (case-insensitive)
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(specifications__icontains=query),
            stock__gt=0
        )[:20]  # limit results for performance
    else:
        products = Product.objects.none()

    # Render results using a template snippet
    html = render_to_string('partials/search_results.html', {'products': products})
    return JsonResponse({'html': html})




def get_recommended_products(user):
    if user.is_authenticated:
        # Popular + in stock
        return Product.objects.filter(stock__gt=0).order_by('-views')[:8]
    else:
        # Random fallback for anonymous users
        return Product.objects.filter(stock__gt=0).order_by('?')[:8]
def get_similar_products(product):
    return Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:6]

@staff_member_required
def most_purchased_products_view(request):
    products = Product.objects.annotate(
        buyers_count=Count('orderitem__order__user', distinct=True),
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:20]  # limit to top 20

    return render(request, 'admin/most_purchased_products.html', {
        'products': products,
    })

@staff_member_required
# Custom Password Form
class CustomPasswordChangeForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username'
    }))
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Current Password'
    }))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'New Password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Confirm Password'
    }))

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        # Prevent insecure username/password combos
        if username.lower() == "admin" or new_password.lower() == "admin":
            raise forms.ValidationError("Username or password cannot be 'admin'.")

        # Enforce strong password length
        if new_password and len(new_password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")

        if new_password != confirm_password:
            raise forms.ValidationError("New password and confirmation do not match.")
        
        return cleaned_data



@staff_member_required
@login_required
def change_password_view(request):
    if request.method == 'POST':
        # PasswordChangeForm handles the old password verification and hashing
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()  # This saves the hashed password to the database
            
            # This is CRITICAL: it updates the session so the user stays logged in
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Your admin key has been updated successfully!')
            return redirect('change_password') # Or redirect to your admin dashboard
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'change_password.html', {
        'form': form
    })




@staff_member_required
# Optional: Only allow existing superusers to add new admins
@user_passes_test(lambda u: u.is_superuser)
def add_admin_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Simple Validation
        if not username or not password:
            messages.error(request, "All fields are required!")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
        else:
            # Create the user and set permissions
            new_admin = User.objects.create_user(username=username, password=password)
            new_admin.is_staff = True  # Allows access to admin site
            new_admin.is_superuser = True # Full permissions
            new_admin.save()
            
            messages.success(request, f"Admin {username} created successfully!")
            return redirect('add_admin_view') # Return 1: After successful POST

    # Return 2: The GET request (This fixes your 'returned None' error)
    return render(request, 'add_admin.html')


def google_login_callback(request):
    # ... your login logic ...
    messages.success(request, f"Hello, {request.user.username}!")
    return redirect('dashboard') # or wherever your dashboard is



def get_dynamic_reviews(product_id):
    # Create a seed based on product ID and the 12-hour window
    # (0 for AM, 1 for PM)
    now = datetime.now()
    time_seed = f"{now.year}{now.month}{now.day}{0 if now.hour < 12 else 1}"
    random.seed(int(f"{product_id}{time_seed}"))

    # Generate fake but realistic data
    rating = round(random.uniform(4.2, 5.0), 1)
    count = random.randint(15, 150)
    
    comments = [
        "Best quality in Nairobi! Delivery was super fast.",
        "Authentic gadget, TingsTech never disappoints.",
        "Value for money. Using it for 2 weeks now, no issues.",
        "The packaging was professional. Highly recommended!",
        "Cheaper than other shops and works perfectly.",
        "Great customer service, SokoBot helped me track my order."
    ]
    
    # Pick 2-3 random reviews
    selected_reviews = random.sample(comments, random.randint(2, 3))
    
    return {
        'rating': rating,
        'count': count,
        'reviews': selected_reviews,
        'stars_html': '★' * int(rating) + '☆' * (5 - int(rating))
    }

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session['cart'] = cart

    return JsonResponse({
        'cart_count': sum(item['quantity'] for item in cart.values())
    })



def update_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('id')
        action = data.get('action') # 'add', 'remove', or 'delete'
        
        product = get_object_or_404(Product, id=product_id)
        
        # Get or create cart item for the logged-in user
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, 
            product=product
        )

        if action == 'add':
            cart_item.quantity += 1
        elif action == 'remove':
            cart_item.quantity -= 1
        
        if action == 'delete' or cart_item.quantity <= 0:
            cart_item.delete()
            return JsonResponse({'status': 'deleted'})
        
        cart_item.save()
        return JsonResponse({'status': 'updated', 'quantity': cart_item.quantity})

def get_cart(request):
    items = CartItem.objects.filter(user=request.user)
    cart_data = [{
        'id': item.product.id,
        'name': item.product.name,
        'price': item.product.price,
        'image': item.product.image.url,
        'quantity': item.quantity
    } for item in items]
    return JsonResponse({'cart': cart_data})




@receiver(pre_save, sender=Brand)
def auto_assign_brand_logo(sender, instance, **kwargs):
    if not instance.logo and instance.name:
        # 1. Create the slug (e.g., "Samsung" -> "samsung")
        brand_slug = slugify(instance.name)
        
        # 2. Define the relative path Django needs
        relative_path = f'brand_master_assets/{brand_slug}.png'
        
        # 3. Define the absolute path to check if the file exists on your PC
        absolute_path = os.path.join(settings.MEDIA_ROOT, 'brand_master_assets', f'{brand_slug}.png')
        
        print(f"DEBUG: Looking for logo at {absolute_path}") # Check your terminal!

        if os.path.exists(absolute_path):
            instance.logo = relative_path
            print(f"DEBUG: Found it! Assigned {relative_path} to {instance.name}")
        else:
            print(f"DEBUG: File not found for {instance.name}")

# app/views.py



@login_required 
def download_receipt(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    template = get_template('payment_instructions.html') # Create this simple HTML file
    context = {'order': order}
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("Error generating PDF", status=400)

from django.shortcuts import render
from .models import Product, Brand, Category

def shop_view(request):
    # Start with all products
    products = Product.objects.all()

    # Capture 'brand' and 'category' IDs from the URL
    brand_id = request.GET.get('brand')
    category_id = request.GET.get('category')

    # Apply Brand filter (using the brand ID)
    if brand_id:
        products = products.filter(brand_id=brand_id)

    # Apply Category filter (using the category ID)
    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        'products': products,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
        'selected_brand': brand_id,
        'selected_category': category_id,
    }
    return render(request, 'your_template.html', context)

from django.shortcuts import redirect
from .models import Order, UserActivity # Ensure these imports match your models
@staff_member_required
def delete_orders(request):
    if request.method == 'POST':
        order_ids = request.POST.getlist('selected_ids')
        Order.objects.filter(id__in=order_ids).delete()
    return redirect('dashboard') # Change this to your dashboard's URL name

@staff_member_required
def delete_logs(request):
    if request.method == 'POST':
        log_ids = request.POST.getlist('selected_ids')
        UserActivity.objects.filter(id__in=log_ids).delete()
    return redirect('dashboard')

@staff_member_required
def delete_orders(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        Order.objects.filter(id__in=selected_ids).delete()
    return redirect('dashboard') 
@staff_member_required
def bulk_delete_products(request):
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        if product_ids:
            # This deletes from DB, so they vanish from index and products pages too
            Product.objects.filter(id__in=product_ids).delete()
    return redirect('manage_products')

from django.shortcuts import redirect
from .models import Order  # Ensure your model name is Order
@staff_member_required
def bulk_delete_orders(request):
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids') # This catches the checkboxes
        if order_ids:
            # This clears the orders and their associated items
            Order.objects.filter(id__in=order_ids).delete()
            
    return redirect('customers')

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

import json
import google.generativeai as genai
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

genai.configure(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
def sokobot_chat(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")

            model = genai.GenerativeModel("models/gemini-2.0-flash")

       
            prompt = f"""
You are SokoBot AI for an ecommerce website called Gadget Soko Kenya.
Answer like a professional customer support AI.

Business Info:
- Name: Gadget Soko Kenya
- Location: CBD, Laxmi Plaza shop number 5
- Delivery: We deliver across all 47 counties in Kenya
- Payments: M-Pesa Till 5280343, Bank Transfer, and POD within Nairobi

Rules:
- Be short and clear
- If asked about products, recommend politely and ask what budget they have
- If asked something unknown, suggest contacting support

Customer message: {user_message}
"""

            response = model.generate_content(prompt)

            return JsonResponse({"reply": response.text})

        except Exception as e:
            return JsonResponse({"reply": f"Error: {str(e)}"}, status=500)

    return JsonResponse({"reply": "Invalid request"}, status=400)

from django.shortcuts import render, get_object_or_404
from .models import Product
from decimal import Decimal

def direct_checkout(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # ❌ Block if out of stock
    if product.stock <= 0:
        messages.error(request, "This product is out of stock.")
        return redirect('product_detail', product_id=product.id)

    # 👇 Fake cart item (single product)
    class SingleItem:
        def __init__(self, product):
            self.product = product
            self.quantity = 1

        @property
        def get_total(self):
            return self.product.final_price * self.quantity

    item = SingleItem(product)

    subtotal = item.get_total
    shipping_nairobi = SiteSettings.objects.first().shipping_fee_nairobi

    context = {
        'cart_items': [item],  # 👈 acts like cart
        'subtotal': subtotal,
        'max_shipping': product.shipping_fee,
        'shipping_nairobi': shipping_nairobi,
        'direct_product': product.id  # 👈 IMPORTANT FLAG
    }
    request.session['direct_product'] = product.id

    return render(request, 'check.html', context)
