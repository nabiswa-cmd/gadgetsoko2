from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from .models import Product, Category, ProductImage, CartItem, Order, OrderItem

import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth
import json
from .models import CartItem

from .models import Brand
from django.db.models import Sum
from .models import CartItem, Brand, Product

from .models import Product, Brand, CartItem
from django.db.models import Sum

def index_view(request):
    products = Product.objects.all()
    brands = Brand.objects.all()

    recommended_products = get_recommended_products(request.user)
    
    quick_sales = Product.objects.filter(
        discount__gt=0,
        stock__gt=0
    ).order_by('-discount')[:8]

    # 🔥 ADDED: Fetch the last 20 products added to the database
    # This orders by the highest ID first (which are the newest inserts)
    featured_products = Product.objects.all().order_by('-id')[:20]

    # ✅ SAFE cart count
    cart_count = 0

    if request.user.is_authenticated:
        result = CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )
        cart_count = result['total'] or 0

    # Added 'featured_products' to the context dictionary below
    return render(request, 'index.html', {
        'products': products,
        'brands': brands,
        'recommended_products': recommended_products,
        'quick_sales': quick_sales,
        'featured_products': featured_products,  # 👈 Pass it to index.html here
        'cart_count': cart_count
    })
# Make sure category_id is included here!
def products_view(request, brand_id=None, category_id=None):
    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    if category_id:
        products = products.filter(category_id=category_id)

    # ... rest of your view logic
    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'current_brand_id': brand_id,
        'current_cat_id': category_id,
    }
    return render(request, 'products.html', context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)

    # AJAX REQUEST
    if request.GET.get('ajax'):
        items = []
        total = 0

        for item in cart_items:
            product = item.product
            price = product.discounted_price if product.discount > 0 else product.price
            item_total = price * item.quantity
            total += item_total

            items.append({
                'id': item.id,
                'name': product.name,
                'brand': product.brand.name,
                'price': price,
                'quantity': item.quantity,
                'item_total': item_total,
                'image': product.images.first().image.url if product.images.first() else '/static/images/default.png'
            })

        return JsonResponse({
            'items': items,
            'total': total,
            'cart_count': sum(item.quantity for item in cart_items)
        })

    # ✅ NORMAL PAGE (THIS WAS MISSING)
    total = sum(item.quantity * item.product.discounted_price for item in cart_items)

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

from .models import Category

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
from .models import ProductView, UserActivity  # add this
from django.shortcuts import render# Ensure Category and Brand are imported

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
import random
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from .models import Product, ProductView, UserActivity # Ensure these are imported
import random
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum

# Remember to align these with your actual model names!
from .models import Product, CartItem, ProductView, UserActivity


# ==========================================
# 1. PRODUCT DETAIL VIEW (Displays page & logs activity)
# ==========================================
def product_detail(request, pk):
    product = get_object_or_404(Product, id=pk)
    
    # --- DYNAMIC REVIEWS & RATINGS LOGIC ---
    now = datetime.now()
    time_chunk = 0 if now.hour < 12 else 1
    seed_value = int(f"{pk}{now.year}{now.month}{now.day}{time_chunk}")
    random.seed(seed_value)

    fake_rating = round(random.uniform(4.4, 5.0), 1)
    fake_count = random.randint(28, 145)
    
    potential_comments = [
        "Best quality in Nairobi! Delivery was super fast.",
        "Authentic gadget, TingsTech never disappoints.",
        "Value for money. Using it for 2 weeks now, no issues.",
        "The packaging was professional. Highly recommended!",
        "Cheaper than other shops and works perfectly.",
        "Great customer service, SokoBot helped me track my order.",
        "Original product. I was skeptical but Gadget Soko is legit.",
        "Fast shipping to Mombasa, received in 24 hours!"
    ]
    
    selected_reviews = random.sample(potential_comments, 3)
    
    social_proof = {
        'rating': fake_rating,
        'count': fake_count,
        'reviews': selected_reviews,
        'stars': '★' * int(fake_rating) + '☆' * (5 - int(fake_rating))
    }
    # ---------------------------------------

    # Increment product views safely
    product.views += 1
    product.save(update_fields=['views'])

    if request.user.is_authenticated:
        # OLD SYSTEM
        ProductView.objects.create(
            user=request.user,
            product=product
        )

        # NEW SYSTEM
        UserActivity.objects.create(
            user=request.user,
            action='VIEW',
            product=product,
            extra_info=f"Viewed {product.name}"
        )

    return render(request, 'product_detail.html', {
        'product': product,
        'social_proof': social_proof
    })


# ==========================================
# 2. ADD TO CART VIEW (Called by AJAX)
# ==========================================
def add_to_cart(request, product_id):
    # Guard rail: Make sure the user is logged in
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login_required'}, status=200)

    product = get_object_or_404(Product, id=product_id)
    
    # Get the cart item if it exists or create a new one with qty 1
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': 1}
    )
    
    # If the item was already in the cart, increment the amount
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Sum up all quantities in the cart for the user to reflect in your top navbar
    result = CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))
    cart_count = result['total'] or 0

    return JsonResponse({
        'success': True,
        'cart_count': cart_count
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
from .models import Brand
from django.utils import timezone
from datetime import timedelta
@login_required

def add_product(request):
    create_default_categories()
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        discount = request.POST.get("discount")
        stock = request.POST.get("stock")
        brand_id = request.POST.get("brand")
        category_id = request.POST.get("category")
        new_category = request.POST.get("new_category")
        offer_days = request.POST.get('offer_days')  # <--- Get the days
        specifications = request.POST.get("specifications")

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

        # ✅ Create product with expiry logic
        product = Product.objects.create(
            name=name,
            price=price,
            discount=discount,
            stock=stock,
            category=category,
            brand=brand,
            specifications=specifications
        )

        # ✅ Set the expiry date if offer_days exists
        if offer_days and int(offer_days) > 0:
            product.discount_expiry = timezone.now() + timedelta(days=int(offer_days))
            product.save()

        images = request.FILES.getlist('images')
        for img in images:
            ProductImage.objects.create(product=product, image=img)

        messages.success(request, f"{product.name} added successfully with a {offer_days}-day offer!")
        return redirect("products")

    return render(request, "add_product.html", {
        "categories": categories,
        "brands": brands
    })

@login_required
def increase_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.quantity += 1
    item.save()
    return JsonResponse({"status": "ok"})


@login_required
def decrease_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()

    return JsonResponse({"status": "ok"})


@login_required
def remove_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({"status": "ok"})

from .models import UserActivity
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import CartItem, Order, OrderItem, UserActivity
# Assuming your M-Pesa function is imported from a utility file
from .utils import lipa_na_mpesa 

def check(request):
    # 1. Fetch Cart Items
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')

    # 2. Calculate Subtotal (using discounted_price as requested)
    subtotal = sum(item.quantity * item.product.discounted_price for item in cart_items)

    if request.method == "POST":
        # --- GET FORM DATA ---
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        region = request.POST.get("region")  # 'nairobi' or 'outside'
        payment_method = request.POST.get("payment_method")

        # --- PHONE NUMBER FORMATTING (M-PESA REQUIREMENT) ---
        # Converts 07... or +254... to 2547...
        clean_phone = phone.strip().replace("+", "")
        if clean_phone.startswith("0"):
            clean_phone = "254" + clean_phone[1:]
        elif not clean_phone.startswith("254"):
            clean_phone = "254" + clean_phone

        # --- CALCULATE SHIPPING & FINAL TOTAL ---
        shipping_fee = 300 if region == "outside" else 0
        final_total = subtotal + shipping_fee

        # --- DETERMINE DESTINATION STRING ---
        location_area = request.POST.get("nairobi_area") if region == "nairobi" else request.POST.get("outside_town")
        full_destination = f"{location_area} - {address}"

        # --- 3. CREATE THE ORDER RECORD ---
        order = Order.objects.create(
            user=request.user,
            name=name,
            email=email,
            phone=clean_phone,
            destination=full_destination,
            total=final_total,
            shipping_fee=shipping_fee, # Recommended to add this field to your Model
            status="Pending",
            payment_status="Awaiting Payment",
            payment_method=payment_method
        )

        # --- 4. CREATE ORDER ITEMS ---
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.discounted_price
            )

        # --- 5. LOG ACTIVITY ---
        UserActivity.objects.create(
            user=request.user,
            action='CHECKOUT',
            extra_info=f"Order #{order.id} | {region} | Total: KES {final_total}"
        )

        # --- 6. HANDLE PAYMENT LOGIC ---
        if payment_method == "mpesa":
            try:
                response = lipa_na_mpesa(
                    phone_number=clean_phone,
                    amount=int(final_total), # M-Pesa API expects Integers
                    account_ref=f"GSK{order.id}",
                    transaction_desc="Gadget Purchase"
                )

                if response.get('ResponseCode') == '0':
                    order.mpesa_checkout_id = response.get('CheckoutRequestID')
                    order.status = 'STK_Sent'
                    order.save()
                    messages.success(request, f"Hambo {name}, M-Pesa prompt sent! Complete it to finish your shopping.")
                else:
                    messages.error(request, "STK Push failed. Please follow manual Paybill instructions.")
            except Exception as e:
                messages.error(request, "Payment gateway error. Please try again.")

        elif payment_method == "pod":
            order.payment_status = "Pay on Delivery"
            order.status = "Confirmed"
            order.save()
            messages.success(request, f"Hello {name}, your order #{order.id} is confirmed! We'll call you for delivery.")

        # --- 7. CLEAR CART & REDIRECT ---
        cart_items.delete() 
        return redirect('payment_instructions', order_id=order.id)

    # --- GET REQUEST: RENDER PAGE ---
    context = {
        'subtotal': subtotal,
        'cart_items': cart_items,
        'shipping_outside': 300
    }
    return render(request, 'check.html', context)

def payment_instructions(request, order_id):
    # Fetch the order and ensure it belongs to the logged-in user
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    return render(request, 'payment_instructions.html', {
        'order': order,
        'method': order.payment_status # Or order.payment_method depending on your model
    })


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Product, CartItem

from django.db.models import Sum
from .models import UserActivity  # 👈 add this

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Product, CartItem, UserActivity


from django import forms
from django.contrib.auth.models import User


from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from .forms import SignupForm


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password1"]

            # username will be email
            user = User.objects.create_user(username=email, email=email, password=password)

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("index")  # redirect after signup

    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})

from django.http import JsonResponse
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth

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
def usersignup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username exists")
            else:
                User.objects.create_user(username=username, email=email, password=password1)
                return redirect('login')
        else:
            messages.error(request, "Passwords do not match")

    return render(request, 'usersignup.html')
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return redirect('login')

        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff:  # ✅ Only staff/admin can access dashboard
                login(request, user)
                messages.success(request, f"Welcome {user.username}! You are logged in as admin.")
                return redirect('dashboard')
            else:
                # ❌ Non-staff trying to access admin
                messages.error(request, "You are not authorized to access the admin dashboard.")
                return redirect('index')  # Redirect normal users
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'login.html')
    
from django.db.models import Q
from .models import Product, Brand
from django.shortcuts import render

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

from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def userlog_view(request):
    if request.method == "POST":
        # Get data from the login form
        username = request.POST.get('username')
        password1 = request.POST.get('password') # Matching your HTML input name

        # 1. Basic validation
        if not username or not password1:
            messages.error(request, "Please enter both username and password")
            return render(request, 'userlog.html') # Replace with your actual login template name

        # 2. Authenticate the user
        user = authenticate(request, username=username, password=password1)

        if user is not None:
            # 3. If credentials are correct, log them in
            login(request, user)
            return redirect('index')
        else:
            # 4. If incorrect, send the error message that triggers the animation
            messages.error(request, "Incorrect details")
            return render(request, 'usersignup.html')

    # GET request: just show the login page
    return render(request, 'usersignup.html')
def logout_view(request):
    logout(request)
    return redirect('index')

from django.db.models import Count, Sum
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict
from django.shortcuts import render
from django.db.models import Sum, Count
from datetime import datetime
from collections import defaultdict
from .models import Product, Order, User

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from collections import defaultdict
from datetime import datetime
from .models import Product, Order, ProductView, User # Make sure all are imported
from collections import defaultdict
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import render
from .models import Product, Order, UserActivity
from django.contrib.auth.models import User

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

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import UserActivity, Order
from django.db.models import Sum

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

from collections import defaultdict
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Product, Order
from django.db.models import Sum

import json
from django.db.models import Sum, Count
from .models import Order, OrderItem # Adjust to your actual models

import json
from django.db.models import Sum
from .models import Order, OrderItem 

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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Order  # Adjust based on your model name

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

from django.shortcuts import redirect, get_object_or_404
from .models import Product

def update_price(request, pk):
    if request.method == "POST":
        product = get_object_or_404(Product, id=pk)
        new_price = request.POST.get("price")

        product.price = new_price
        product.save()

    return redirect('manage_products')

from django.shortcuts import redirect, get_object_or_404
from .models import Product

def mark_out_of_stock(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        product.in_stock = 0  # or whatever field you use
        product.save()
    return redirect('manage_products')
    # app/views.py
from django.shortcuts import render
from django.http import JsonResponse
from .models import Product

from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Product

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


from .models import Product


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

from django.db.models import Sum,Count
@staff_member_required
def most_purchased_products_view(request):
    products = Product.objects.annotate(
        buyers_count=Count('orderitem__order__user', distinct=True),
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:20]  # limit to top 20

    return render(request, 'admin/most_purchased_products.html', {
        'products': products,
    })
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django import forms

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


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required

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
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test

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
from django.contrib import messages

def google_login_callback(request):
    # ... your login logic ...
    messages.success(request, f"Hello, {request.user.username}!")
    return redirect('dashboard') # or wherever your dashboard is


import random
from datetime import datetime

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
def update_cart(request, product_id):
    action = request.GET.get('action')
    cart = request.session.get('cart', {})

    product_id = str(product_id)

    if product_id not in cart:
        return JsonResponse({"error": "Item not in cart"})

    if action == 'increase':
        cart[product_id]['quantity'] += 1

    elif action == 'decrease':
        cart[product_id]['quantity'] -= 1
        if cart[product_id]['quantity'] <= 0:
            del cart[product_id]

    request.session['cart'] = cart

    return JsonResponse({
        'cart_count': sum(item['quantity'] for item in cart.values())
    })