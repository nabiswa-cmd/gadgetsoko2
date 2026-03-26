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

def index_view(request):
    products = Product.objects.all()
    brands = Brand.objects.all()

    recommended_products = get_recommended_products(request.user)
    quick_sales = Product.objects.filter(
        discount__gt=0,
        stock__gt=0
    ).order_by('-discount')[:8]

    # ✅ SAFE cart count
    cart_count = 0

    if request.user.is_authenticated:
        result = CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )
        cart_count = result['total'] or 0

    return render(request, 'index.html', {
        'products': products,
        'brands': brands,
        'recommended_products': recommended_products,
        'quick_sales': quick_sales,
        'cart_count': cart_count
    })

def products_view(request):
    category_id = request.GET.get('category')

    if category_id:
        products = Product.objects.filter(category_id=category_id)
    else:
        products = Product.objects.all()

    categories = Category.objects.all()
    brands = Brand.objects.all()  # ✅ ADD THIS

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'brands': brands  # ✅ CRITICAL
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
@login_required
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

def product_detail(request, pk):
    product = get_object_or_404(Product, id=pk)
    
    # Increment product views safely
    product.views += 1
    product.save(update_fields=['views'])

    if request.user.is_authenticated:
        # OLD SYSTEM (keep it)
        ProductView.objects.create(
            user=request.user,
            product=product
        )

        # NEW SYSTEM (powerful tracking)
        UserActivity.objects.create(
            user=request.user,
            action='VIEW',
            product=product,
            extra_info=f"Viewed {product.name}"
        )

    return render(request, 'product_detail.html', {'product': product})
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

@login_required
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
        specifications = request.POST.get("specifications")

        # ✅ Validate brand
        if not brand_id:
            messages.error(request, "Please select a brand.")
            return redirect("add_product")

        brand = Brand.objects.get(id=brand_id)

        # ✅ Handle category safely
        if new_category:
            category = Category.objects.create(name=new_category)
        else:
            if not category_id:
                messages.error(request, "Please select or create a category.")
                return redirect("add_product")
            category = Category.objects.get(id=category_id)

        # ✅ Create product
        product = Product.objects.create(
            name=name,
            price=price,
            discount=discount,
            stock=stock,
            category=category,
            brand=brand,
            specifications=specifications
        )

        # ✅ Save images
        images = request.FILES.getlist('images')
        for img in images:
            ProductImage.objects.create(product=product, image=img)

        return redirect("products")

    return render(request, "add_product.html", {
        "categories": categories,
        "brands": brands
    })

    return render(request, "add_product.html", {
        "categories": categories,
        "brands": brands  # ✅ CRITICAL
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

@login_required
@login_required
def check(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')

    # Calculate subtotal from cart items
    subtotal = sum(item.quantity * item.product.discounted_price for item in cart_items)

    if request.method == "POST":
        # 1. GET FORM DATA
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        region = request.POST.get("region") # 'nairobi' or 'outside'
        payment_method = request.POST.get("payment_method") # 'mpesa', 'equity', 'pochi', 'pod'
        
        # 2. CALCULATE TOTALS
        shipping_fee = 300 if region == "outside" else 0
        final_total = subtotal + shipping_fee

        # Determine location area for the destination string
        if region == "nairobi":
            location_area = request.POST.get("nairobi_area")
        else:
            location_area = request.POST.get("outside_town")

        # 3. CREATE THE ORDER RECORD
        # Note: Ensure these fields (destination, payment_status) exist in your Order model
        order = Order.objects.create(
            user=request.user,
            name=name,
            email=email,
            phone=phone,
            destination=f"{location_area} - {address}",
            total=final_total,
            status="Pending",
            payment_status="Awaiting Payment"
        )

        # 4. CREATE ORDER ITEMS
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.discounted_price
            )

        # 5. LOG ACTIVITY
        UserActivity.objects.create(
            user=request.user,
            action='CHECKOUT',
            extra_info=f"Order #{order.id} Created | Method: {payment_method} | Total: KES {final_total}"
        )

        # 6. HANDLE SPECIFIC PAYMENT LOGIC
        
        if payment_method == "mpesa":
            # Trigger STK Push
            response = lipa_na_mpesa(
                phone_number=phone,
                amount=final_total,
                account_ref=f"GSK{order.id}",
                transaction_desc="Gadget Purchase"
            )

            if response.get('ResponseCode') == '0':
                order.mpesa_checkout_id = response.get('CheckoutRequestID')
                order.status = 'STK_Sent'
                order.save()
                messages.success(request, "M-Pesa prompt sent to your phone.")
            else:
                messages.error(request, "M-Pesa push failed. Please use the manual instructions below.")

        elif payment_method == "pod":
            order.payment_status = "Pay on Delivery"
            order.status = "Confirmed"
            order.save()
            messages.success(request, f"Order #{order.id} confirmed for delivery.")

        # 7. FINAL STEPS
        cart_items.delete() # Clear the cart after order is safely in DB
        
        # This redirect provides the order_id that your URL pattern requires
        return redirect('payment_instructions', order_id=order.id)

    # GET request: Show the checkout page
    return render(request, 'check.html', {'total': subtotal})

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

def add_to_cart(request, product_id):
    # 🔐 HANDLE NOT LOGGED IN (AJAX SAFE)
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'login_required',
            'message': 'Please login to add items to cart'
        }, status=403)

    product = get_object_or_404(Product, id=product_id)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()
        action_text = "Increased quantity"
    else:
        action_text = "Added to cart"

    # 🔥 TRACK ACTIVITY
    UserActivity.objects.create(
        user=request.user,
        action='CART',
        product=product,
        extra_info=f"{action_text}: {product.name} (Qty: {cart_item.quantity})"
    )

    total = CartItem.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return JsonResponse({
        'cart_count': total,
        'product_name': product.name
    })

# ================= AUTH =================
def signup_view(request):
    if request.method == 'POST':
        User.objects.create_user(
            username=request.POST.get('username'),
            email=request.POST.get('email'),
            password=request.POST.get('password')
        )
        return redirect('login')

    return render(request, 'signup.html')

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


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )

        if user:
            login(request, user)
            return redirect('dashboard' if user.is_staff else 'index')

        messages.error(request, "Invalid credentials")

    return render(request, 'login.html')

from django.contrib.auth import login

def userlog_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username exists")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                is_staff=False  # ✅ ensure user is not staff
            )
            login(request, user)  # ✅ log them in immediately
            return redirect('index')  # ✅ redirect to normal homepage

    return render(request, 'usersignup.html')

def logout_view(request):
    logout(request)
    return redirect('login')

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

@staff_member_required
def dashboard_view(request):
    # Basic stats
    products_count = Product.objects.count()
    orders_count = Order.objects.count()
    users_count = User.objects.count()
    revenue = Order.objects.aggregate(total_revenue=Sum('total'))['total_revenue'] or 0

    # Recent orders
    recent_orders = Order.objects.order_by('-id')[:5]

    # --- NEW: CUSTOMER ACTIVITY LOGS ---
    # Fetch the last 15 product views, including the User and Product info
    activity_logs = UserActivity.objects.select_related('user', 'product').order_by('-timestamp')[:20]

    for log in activity_logs:
        # For each log, find the most recent order by this specific user
        # to see where their transaction currently stands
        latest_order = Order.objects.filter(user=log.user).order_by('-created_at').first()
        if latest_order:
            log.last_order_status = latest_order.status
        else:
            log.last_order_status = "Browsing Only"
    # ------------------------------------

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
        total_sold=Sum('orderitem__quantity'),
        # total_sold=Sum('items__quantity'), # Use 'items' if that is your related_name
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
        "customer_activity": activity_logs, # New context for the table
        "products": Product.objects.all(),
    }

    return render(request, "dashboard.html", context)

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

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']

            # Authenticate user with current password
            user = authenticate(username=username, password=current_password)
            if user is None or user != request.user:
                messages.error(request, "Incorrect username or current password.")
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Password changed successfully.")
                return redirect('dashboard')
    else:
        form = CustomPasswordChangeForm()

    return render(request, 'change_password.html', {'form': form})

    from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def add_admin_view(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        email = request.POST.get("email").strip()

        # Prevent adding forbidden usernames
        if username.lower() in ["admin", "administrator"]:
            messages.error(request, "Username not allowed.")
            return redirect('add_admin')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        else:
            # Default password
            default_password = "bugbugGADGET"

            # Create admin user

from django.contrib import messages

def google_login_callback(request):
    # ... your login logic ...
    messages.success(request, f"Hello, {request.user.username}!")
    return redirect('dashboard') # or wherever your dashboard is
           