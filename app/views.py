import os
import requests
import base64
import json
import random
import logging
import traceback
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from decimal import Decimal
from collections import defaultdict
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
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
from django.db.models import Sum, F, Q, Count, Value, ExpressionWrapper, DateTimeField, DurationField
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import render_to_string, get_template
from django.core.paginator import Paginator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.timezone import now as tz_now
from django import forms
from xhtml2pdf import pisa

from .models import (
    Product, Category, ProductImage, CartItem, Order, OrderItem,
    SiteSettings, Brand, ProductView, UserActivity, EmailOTP, SignupOTP,UserProfile
)
from .forms import SignupForm

from google import genai

# ─────────────────────────────────────────────
# Logger — replaces ALL print() calls
# Gunicorn/Nginx pick this up via Django's
# LOGGING setting in settings.py
# ─────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# EMAIL HELPERS  (HTML format matching brand template)
# ═══════════════════════════════════════════════════════════

def _send_html_email(subject, to_email, html_content, plain_text):
    """
    Central helper — always sends both plain-text and HTML parts.
    Errors are logged; they never bubble up and crash a view.
    """
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info("Email sent to %s | subject: %s", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s | subject: %s", to_email, subject)


def _email_wrapper(inner_html: str) -> str:
    """Wraps any inner content block in the standard Gadget Soko branded shell."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background-color:#ffffff;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#ffffff;">
    <tr>
      <td align="center">
        <table border="0" cellpadding="0" cellspacing="0" width="500" style="background-color:#ffffff;">

          <!-- LOGO -->
          <tr>
            <td align="center" style="padding:40px 0 20px 0;border-bottom:2px solid #f4330c;">
              <img src="https://gadgetsoko.com/static/images/android-chrome-512x512.png"
                   alt="Gadget Soko" width="140"
                   style="display:block;border:0;">
            </td>
          </tr>

          <!-- CONTENT -->
          {inner_html}

          <!-- FOOTER -->
          <tr>
            <td style="padding:40px 20px;border-top:1px solid #e2e8f0;text-align:center;">
              <p style="color:#64748b;font-size:11px;margin:0;text-transform:uppercase;letter-spacing:1px;">
                &copy; 2026 GADGET SOKO | TECH &amp; RETAIL<br>
                <span style="margin-top:10px;display:block;color:#94a3b8;">
                  Delivering the future to your doorstep.
                </span>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_welcome_email(username: str, to_email: str):
    """OTP verification success → welcome email."""
    inner = f"""
    <tr>
      <td style="padding:50px 20px;text-align:center;">
        <h2 style="color:#0b3a63;font-size:24px;margin:0 0 10px 0;
                   font-weight:bold;text-transform:uppercase;letter-spacing:2px;">
          Welcome, {username}
        </h2>
        <p style="color:#1e293b;font-size:16px;line-height:26px;margin:0 0 35px 0;">
          Your account at <strong>Gadget Soko</strong> is now active.
          You are ready to explore the latest innovations in tech.
        </p>
        <a href="https://gadgetsoko.com"
           style="background-color:#f4330c;color:#ffffff;padding:18px 45px;
                  text-decoration:none;font-size:13px;font-weight:bold;
                  display:inline-block;text-transform:uppercase;letter-spacing:2px;">
          Start Exploring
        </a>
      </td>
    </tr>"""

    html = _email_wrapper(inner)
    plain = f"Welcome {username}!\n\nYour Gadget Soko account is now active.\nVisit https://gadgetsoko.com to start exploring."
    _send_html_email("Welcome to Gadget Soko 🎉", to_email, html, plain)


def send_otp_email(username: str, to_email: str, otp: str):
    """Sends OTP verification code."""
    inner = f"""
    <tr>
      <td style="padding:50px 20px;text-align:center;">
        <h2 style="color:#0b3a63;font-size:24px;margin:0 0 10px 0;
                   font-weight:bold;text-transform:uppercase;letter-spacing:2px;">
          Verify Your Account
        </h2>
        <p style="color:#1e293b;font-size:16px;line-height:26px;margin:0 0 20px 0;">
          Hi <strong>{username}</strong>, use the code below to complete your registration.
          It expires in <strong>10 minutes</strong>.
        </p>
        <div style="background-color:#f8fafc;border:2px solid #f4330c;
                    display:inline-block;padding:20px 40px;margin:0 0 30px 0;">
          <span style="font-size:36px;font-weight:bold;color:#0b3a63;
                       letter-spacing:8px;">{otp}</span>
        </div>
        <p style="color:#64748b;font-size:13px;margin:0;">
          If you did not request this, please ignore this email.
        </p>
      </td>
    </tr>"""

    html = _email_wrapper(inner)
    plain = f"Hi {username},\n\nYour Gadget Soko OTP code is: {otp}\nIt expires in 10 minutes.\n\nIf you did not request this, ignore this email."
    _send_html_email("Gadget Soko — OTP Verification", to_email, html, plain)


def send_order_confirmation_email(order, name: str, to_email: str,
                                   items_summary_html: str, items_summary_plain: str,
                                   shipping_fee, final_total, receipt_url: str,
                                   region: str = "nairobi"):
    """Order placed → confirmation email with product images, correct shipping, receipt link."""

    # Shipping label shown in email
    shipping_location = "Within Nairobi" if region == "nairobi" else "Upcountry Delivery"

    inner = f"""
    <tr>
      <td style="padding:40px 20px;">
        <h2 style="color:#0b3a63;font-size:22px;margin:0 0 6px 0;
                   font-weight:bold;text-transform:uppercase;letter-spacing:2px;
                   text-align:center;">
          Order Confirmed ✓
        </h2>
        <p style="color:#64748b;font-size:13px;text-align:center;margin:0 0 30px 0;">
          Order Reference: <strong>#{order.id}</strong>
        </p>

        <p style="color:#1e293b;font-size:15px;line-height:24px;margin:0 0 20px 0;">
          Hello <strong>{name}</strong>,<br>
          Thank you for your purchase! Here is a summary of your order.
        </p>

        <!-- Items table — 3 columns: image | name+qty | price -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%"
               style="border-top:2px solid #f4330c;margin-bottom:20px;">
          <tr style="background-color:#0b3a63;">
            <td style="padding:10px 10px;color:#ffffff;font-size:12px;
                       font-weight:bold;text-transform:uppercase;letter-spacing:1px;
                       width:60px;">Photo</td>
            <td style="padding:10px 14px;color:#ffffff;font-size:12px;
                       font-weight:bold;text-transform:uppercase;letter-spacing:1px;">Item</td>
            <td style="padding:10px 14px;color:#ffffff;font-size:12px;
                       font-weight:bold;text-transform:uppercase;letter-spacing:1px;
                       text-align:right;">Amount</td>
          </tr>
          {items_summary_html}
          <tr style="background-color:#f8fafc;">
            <td style="padding:10px 10px;"></td>
            <td style="padding:10px 14px;color:#1e293b;font-size:13px;">
              Shipping — <em style="color:#64748b;">{shipping_location}</em>
            </td>
            <td style="padding:10px 14px;color:#1e293b;font-size:13px;
                       text-align:right;font-weight:600;">KES {int(shipping_fee):,}</td>
          </tr>
          <tr style="background-color:#0b3a63;">
            <td style="padding:12px 10px;"></td>
            <td style="padding:12px 14px;color:#ffffff;font-size:14px;font-weight:bold;">
              TOTAL
            </td>
            <td style="padding:12px 14px;color:#f4330c;font-size:16px;
                       font-weight:bold;text-align:right;">
              KES {int(final_total):,}
            </td>
          </tr>
        </table>

        <div style="text-align:center;margin-top:30px;">
          <a href="{receipt_url}"
             style="background-color:#f4330c;color:#ffffff;padding:16px 40px;
                    text-decoration:none;font-size:13px;font-weight:bold;
                    display:inline-block;text-transform:uppercase;letter-spacing:2px;">
            Download Receipt
          </a>
        </div>
      </td>
    </tr>"""

    html = _email_wrapper(inner)
    plain = (
        f"Hello {name},\n\nYour order #{order.id} has been received.\n\n"
        f"Items:\n{items_summary_plain}\n"
        f"Shipping ({shipping_location}): KES {int(shipping_fee):,}\n"
        f"Total: KES {int(final_total):,}\n\n"
        f"Download Receipt:\n{receipt_url}\n\n"
        f"Thank you for shopping with us!"
    )
    _send_html_email(f"Order Confirmed * Gadget Soko #{order.id}", to_email, html, plain)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def create_default_categories():
    categories = [
        "Kitchen Appliances", "Phones & Tablets", "Computers & Laptops",
        "TVs & Entertainment", "Audio Devices", "Networking Equipment",
        "Home Appliances", "Power & Electrical Accessories", "Cables & Connectors",
        "Batteries & Power Banks", "Lighting Equipment", "CCTV & Security Systems",
        "Gaming Accessories", "Smart Home Devices", "Wearables", "Office Electronics",
        "Printers & Scanners", "Computer Accessories", "Mobile Accessories",
        "Solar & Energy Solutions", "Extension Cables & Adaptors", "Chargers & Adapters",
        "Fans & Cooling Systems", "Irons & Heating Appliances", "Fridges & Freezers",
        "Cookers & Ovens", "Blenders & Mixers", "Microwaves", "Electric Kettles",
    ]
    for cat in categories:
        Category.objects.get_or_create(name=cat)


def get_recommended_products(user):
    if user.is_authenticated:
        return Product.objects.filter(stock__gt=0).order_by('-views')[:8]
    return Product.objects.filter(stock__gt=0).order_by('?')[:8]


def get_similar_products(product):
    return Product.objects.filter(category=product.category).exclude(id=product.id)[:6]


def get_dynamic_reviews(product_id):
    now = datetime.now()
    time_seed = f"{now.year}{now.month}{now.day}{0 if now.hour < 12 else 1}"
    random.seed(int(f"{product_id}{time_seed}"))
    rating = round(random.uniform(4.2, 5.0), 1)
    count = random.randint(15, 150)
    comments = [
        "Best quality in Nairobi! Delivery was super fast.",
        "Authentic gadget, TingsTech never disappoints.",
        "Value for money. Using it for 2 weeks now, no issues.",
        "The packaging was professional. Highly recommended!",
        "Cheaper than other shops and works perfectly.",
        "Great customer service, SokoBot helped me track my order.",
    ]
    selected_reviews = random.sample(comments, random.randint(2, 3))
    return {
        'rating': rating,
        'count': count,
        'reviews': selected_reviews,
        'stars_html': '★' * int(rating) + '☆' * (5 - int(rating)),
    }


# ═══════════════════════════════════════════════════════════
# M-PESA
# ═══════════════════════════════════════════════════════════

def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception:
        logger.exception("Failed to get M-Pesa access token")
        return None


def lipa_na_mpesa(phone_number, amount, account_ref, transaction_desc):
    token = get_mpesa_access_token()
    if not token:
        return {"error": "Failed to generate access token"}

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
        "TransactionDesc": transaction_desc,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=15,
        )
        logger.info("M-Pesa STK push status: %s", response.status_code)
        return response.json()
    except requests.exceptions.JSONDecodeError:
        logger.error("M-Pesa STK push — invalid JSON response (status %s)", response.status_code)
        return {
            "error": "Invalid JSON response from MPESA STK Push",
            "status_code": response.status_code,
        }
    except Exception:
        logger.exception("M-Pesa STK push request failed")
        return {"error": "M-Pesa request exception"}


def register_mpesa_urls(request):
    access_token = get_mpesa_access_token()
    api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "ShortCode": settings.MPESA_SHORTCODE,
        "ResponseType": "Completed",
        "ConfirmationURL": "https://eloy-headstrong-eventfully.ngrok-free.dev/payment_callback/",
        "ValidationURL": "https://eloy-headstrong-eventfully.ngrok-free.dev/payment_callback/",
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        return JsonResponse(response.json())
    except Exception:
        logger.exception("Failed to register M-Pesa URLs")
        return JsonResponse({"error": "Registration failed"}, status=500)


# ═══════════════════════════════════════════════════════════
# PUBLIC VIEWS
# ═══════════════════════════════════════════════════════════

def index_view(request):
    now = timezone.now()

    active_products_query = Product.objects.annotate(
        expiry=ExpressionWrapper(
            F('discount_start_time') + (
                F('discount_duration_hours') * Value(timedelta(hours=1), output_field=DurationField())
            ),
            output_field=DateTimeField()
        )
    )

    # Clean up expired discounts
    try:
        expired_ids = list(
            active_products_query.filter(
                discount_start_time__isnull=False,
                expiry__lt=now
            ).values_list('id', flat=True)
        )
        if expired_ids:
            Product.objects.filter(id__in=expired_ids).update(
                discount=0,
                discount_start_time=None,
                discount_duration_hours=0,
            )
            logger.info("Cleared expired discounts for %d products", len(expired_ids))
    except Exception:
        logger.exception("Error cleaning up expired discounts")

    brands = Brand.objects.all()

    quick_sales = list(
        active_products_query.filter(
            discount__gt=0,
            stock__gt=0,
            discount_start_time__isnull=False,
            expiry__gt=now,
        ).order_by('-discount')[:8]
    )

    all_featured = Product.objects.all().order_by('-id')
    paginator = Paginator(all_featured, 24)
    featured_products = paginator.get_page(request.GET.get('page'))

    cart_count = 0
    if request.user.is_authenticated:
        result = CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))
        cart_count = result['total'] or 0

    return render(request, 'index.html', {
        'brands': brands,
        'quick_sales': quick_sales,
        'featured_products': featured_products,
        'cart_count': cart_count,
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

    paginator = Paginator(products_list, 30)
    products = paginator.get_page(request.GET.get('page'))

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'brands': brands,
        'selected_brand': brand_id,
        'selected_category': category_id,
    })


def products_by_category_view(request, brand_id=None, category_id=None):
    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if brand_id:
        products = products.filter(brand_id=brand_id)
    if category_id:
        products = products.filter(category_id=category_id)

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'brands': brands,
        'current_brand_id': brand_id,
        'current_cat_id': category_id,
    })


def products_by_brand(request, brand_id):
    products = Product.objects.filter(brand__id=brand_id)
    return render(request, 'products.html', {
        'products': products,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, id=pk)

    if product.stock <= 0:
        messages.error(request, "This product is currently out of stock.")
        return redirect('products')

    now_time = datetime.now()
    seed_value = int(f"{pk}{now_time.day}{now_time.hour // 12}")
    random.seed(seed_value)

    fake_rating = round(random.uniform(4.4, 5.0), 1)
    social_proof = {
        'rating': fake_rating,
        'count': random.randint(28, 145),
        'stars': '★' * int(fake_rating) + '☆' * (5 - int(fake_rating)),
    }

    Product.objects.filter(id=pk).update(views=F('views') + 1)

    recommended = (
        Product.objects.filter(category=product.category)
        .exclude(id=product.id)
        .order_by('?')[:10]
    )

    return render(request, 'product_detail.html', {
        'product': product,
        'social_proof': social_proof,
        'recommended_products': recommended,
        'discount_expiry': product.discount_expiry.isoformat() if product.discount_expiry else None,
    })


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


def live_search(request):
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(specifications__icontains=query),
            stock__gt=0,
        )[:20]
    else:
        products = Product.objects.none()
    html = render_to_string('partials/search_results.html', {'products': products})
    return JsonResponse({'html': html})


def shop_view(request):
    products = Product.objects.all()
    brand_id = request.GET.get('brand')
    category_id = request.GET.get('category')

    if brand_id:
        products = products.filter(brand_id=brand_id)
    if category_id:
        products = products.filter(category_id=category_id)

    return render(request, 'your_template.html', {
        'products': products,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
        'selected_brand': brand_id,
        'selected_category': category_id,
    })


# ═══════════════════════════════════════════════════════════
# CART
# ═══════════════════════════════════════════════════════════

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
        return JsonResponse({'items': items, 'total': float(total), 'cart_count': cart_count})

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    })


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

    cart_count = (
        CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
    )
    return JsonResponse({"success": True, "cart_count": cart_count})


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
    item.delete()
    return JsonResponse({"success": True, "quantity": 0, "removed": True})


@login_required
def remove_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({"success": True})


def remove_from_cart(request, product_id):
    """Session-based cart removal (guest users)."""
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    if product_id in cart:
        del cart[product_id]
    request.session['cart'] = cart
    return JsonResponse({'cart_count': sum(item['quantity'] for item in cart.values())})


def update_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    data = json.loads(request.body)
    product_id = data.get('id')
    action = data.get('action')

    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)

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
        'quantity': item.quantity,
    } for item in items]
    return JsonResponse({'cart': cart_data})


# ═══════════════════════════════════════════════════════════
# CHECKOUT
# ═══════════════════════════════════════════════════════════
@login_required
def check(request):
    config, _ = SiteSettings.objects.get_or_create(id=1)

    # ── Fetch (or create) the user's profile for autofill ──
    try:
        user_profile = request.user.profile
    except Exception:
        from .models import UserProfile
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    direct_product_id = request.session.get('direct_product')

    if direct_product_id:
        product = get_object_or_404(Product, id=direct_product_id)

        class SingleItem:
            def __init__(self, p):
                self.product = p
                self.quantity = 1

        cart_items = [SingleItem(product)]
        is_direct = True
    else:
        cart_items = CartItem.objects.filter(user=request.user)
        is_direct = False

    if not is_direct and not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')

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

    subtotal = sum(item.quantity * item.product.final_price for item in cart_items)

    # Fixed shipping: KES 200 within Nairobi, KES 500 upcountry
    SHIPPING_NAIROBI = Decimal('200.00')
    SHIPPING_OUTSIDE = Decimal('500.00')

    if request.method == "POST":
        try:
            with transaction.atomic():
                name = request.POST.get("name")
                email = request.POST.get("email")
                phone = request.POST.get("phone")
                address = request.POST.get("address")
                region = request.POST.get("region")
                payment_method = request.POST.get("payment_method")

                # ── Hardcoded shipping: 200 Nairobi, 500 upcountry ──
                shipping_fee = SHIPPING_NAIROBI if region == "nairobi" else SHIPPING_OUTSIDE
                final_total = subtotal + shipping_fee

                clean_phone = phone.strip().replace("+", "")
                if clean_phone.startswith("0"):
                    clean_phone = "254" + clean_phone[1:]
                elif not clean_phone.startswith("254"):
                    clean_phone = "254" + clean_phone

                location_area = (
                    request.POST.get("nairobi_area")
                    if region == "nairobi"
                    else request.POST.get("outside_town")
                )
                full_destination = f"{location_area} - {address}"

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
                    payment_method=payment_method,
                )

                # Build items HTML rows (with product image) and plain text
                items_html_rows = ""
                items_plain = ""

                # Build absolute base URL once — used for all image URLs in email
                protocol = 'https' if request.is_secure() else 'http'
                domain = request.get_host()
                base_url = f"{protocol}://{domain}"

                for item in cart_items:
                    product = item.product
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.final_price,
                    )
                    product.stock -= item.quantity
                    product.save()

                    # ── Resolve product image URL for email ──
                    img_url = None

                    try:
                        first_pi = product.images.first()
                        if first_pi and first_pi.image:
                            img_url = base_url + first_pi.image.url
                    except Exception:
                        pass

                    if not img_url:
                        try:
                            if product.image and product.image.name:
                                img_url = base_url + product.image.url
                        except Exception:
                            pass

                    if not img_url:
                        img_url = "https://via.placeholder.com/52x52?text=No+Image"

                    line_total = int(product.final_price * item.quantity)

                    items_html_rows += (
                        f"<tr>"
                        f"<td style='padding:8px 10px;border-bottom:1px solid #e2e8f0;"
                        f"width:68px;vertical-align:middle;'>"
                        f"<img src='{img_url}' alt='' width='52' height='52' "
                        f"style='border-radius:6px;object-fit:cover;display:block;"
                        f"border:1px solid #e2e8f0;'>"
                        f"</td>"
                        f"<td style='padding:8px 14px;color:#1e293b;font-size:13px;"
                        f"border-bottom:1px solid #e2e8f0;vertical-align:middle;'>"
                        f"<strong>{product.name}</strong><br>"
                        f"<span style='color:#64748b;font-size:12px;'>Qty: {item.quantity}</span>"
                        f"</td>"
                        f"<td style='padding:8px 14px;color:#1e293b;font-size:13px;"
                        f"border-bottom:1px solid #e2e8f0;text-align:right;"
                        f"vertical-align:middle;white-space:nowrap;font-weight:600;'>"
                        f"KES {line_total:,}</td>"
                        f"</tr>"
                    )
                    items_plain += (
                        f"- {product.name} (x{item.quantity}) "
                        f"@ KES {int(product.final_price):,} = KES {line_total:,}\n"
                    )

                receipt_url = f"{protocol}://{domain}{reverse('download_receipt', args=[order.id])}"

                send_order_confirmation_email(
                    order=order,
                    name=name,
                    to_email=email,
                    items_summary_html=items_html_rows,
                    items_summary_plain=items_plain,
                    shipping_fee=shipping_fee,
                    final_total=final_total,
                    receipt_url=receipt_url,
                    region=region,
                )

                # M-Pesa STK push
                if payment_method == "mpesa":
                    try:
                        response = lipa_na_mpesa(
                            phone_number=clean_phone,
                            amount=int(final_total),
                            account_ref=f"GSK{order.id}",
                            transaction_desc="Gadget Purchase",
                        )
                        if response.get('ResponseCode') == '0':
                            order.checkout_request_id = response.get('CheckoutRequestID')
                            order.status = 'STK_Sent'
                            order.save()
                        else:
                            logger.warning(
                                "M-Pesa STK push failed for order %s: %s",
                                order.id, response
                            )
                            messages.error(request, "M-Pesa request failed. Please try again.")
                    except Exception:
                        logger.exception("M-Pesa error for order %s", order.id)
                        messages.error(request, "M-Pesa request failed.")

                elif payment_method == "pod":
                    order.payment_status = "Pay on Delivery"
                    order.status = "Confirmed"
                    order.save()

                if is_direct:
                    request.session.pop('direct_product', None)
                else:
                    cart_items.delete()

                messages.success(request, f"Order #{order.id} placed successfully!")
                return redirect('payment_instructions', order_id=order.id)

        except Exception:
            logger.exception("Checkout error for user %s", request.user.id)
            messages.error(request, "Something went wrong. Please try again.")
            return redirect('view_cart')

    return render(request, 'check.html', {
        'subtotal': subtotal,
        'cart_items': cart_items,
        'config': config,
        'shipping_nairobi': config.shipping_fee_nairobi,
        'max_shipping': SHIPPING_OUTSIDE,
        'user_profile': user_profile,          # ← added
    })


def direct_checkout(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.stock <= 0:
        messages.error(request, "This product is out of stock.")
        return redirect('product_detail', pk=product.id)

    class SingleItem:
        def __init__(self, p):
            self.product = p
            self.quantity = 1

        @property
        def get_total(self):
            return self.product.final_price * self.quantity

    item = SingleItem(product)
    subtotal = item.get_total
    config, _ = SiteSettings.objects.get_or_create(id=1)

    request.session['direct_product'] = product.id

    return render(request, 'check.html', {
        'cart_items': [item],
        'subtotal': subtotal,
        'shipping_nairobi': config.shipping_fee_nairobi,   # KES 200
        'max_shipping': Decimal('500.00'),                  # KES 500 upcountry
        'config': config,
        'direct_product': product.id,
    })


def payment_instructions(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'payment_instructions.html', {
        'order': order,
        'method': order.payment_status,
    })


@login_required
def download_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template = get_template('payment_instructions.html')
    html = template.render({'order': order})
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    logger.error("PDF generation failed for order %s", order_id)
    return HttpResponse("Error generating PDF", status=400)


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════

def usersignup_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

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
            SignupOTP.objects.update_or_create(
                email=email,
                defaults={"username": username, "password": password1, "otp": otp},
            )
            send_otp_email(username=username, to_email=email, otp=otp)
            request.session["signup_email"] = email
            messages.success(request, "OTP has been sent to your email. Please verify.")
            return redirect("verify_signup_otp")

    return render(request, 'signup.html')


def verify_signup_otp(request):
    email = request.session.get("signup_email")

    if not email:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("signup")

    try:
        otp_obj = SignupOTP.objects.get(email=email)
    except SignupOTP.DoesNotExist:
        messages.error(request, "OTP not found. Please sign up again.")
        return redirect("signup")

    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()

        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, "OTP expired. Please sign up again.")
            return redirect("signup")

        if otp_input != otp_obj.otp:
            messages.error(request, "Invalid OTP. Try again.")
            return redirect("verify_signup_otp")

        user = User.objects.create_user(
            username=otp_obj.username,
            email=otp_obj.email,
            password=otp_obj.password,
        )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        otp_obj.delete()
        request.session.pop("signup_email", None)

        # Send branded welcome email
        send_welcome_email(username=user.username, to_email=user.email)

        messages.success(request, f"Account created successfully! Welcome {user.username} 🎉")
        return redirect("index")

    return render(request, "verify_otp.html", {"email": email})


def userlog_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == "POST":
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username_or_email or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'login.html')

        user = authenticate(request, username=username_or_email, password=password)

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


def secretkey_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff:
                login(request, user)
                messages.success(request, f"Access Granted. Welcome, Admin {user.username}.")
                return redirect('dashboard')
            else:
                messages.error(request, "Unauthorized access. Staff only.")
                return redirect('index')
        else:
            messages.error(request, "Invalid admin credentials.")
            return redirect('secretkey')

    return render(request, 'admin_login_template.html')


def logout_view(request):
    logout(request)
    return redirect('index')


def google_login_callback(request):
    messages.success(request, f"Hello, {request.user.username}!")
    return redirect('dashboard')


# ═══════════════════════════════════════════════════════════
# STAFF / ADMIN VIEWS
# ═══════════════════════════════════════════════════════════

@staff_member_required
def dashboard_view(request):
    products_count = Product.objects.count()
    orders_count = Order.objects.count()
    users_count = User.objects.count()
    revenue = Order.objects.aggregate(total_revenue=Sum('total'))['total_revenue'] or 0

    recent_orders = Order.objects.order_by('-id')[:5]

    activity_logs = (
        UserActivity.objects.select_related('user', 'product').order_by('-timestamp')[:20]
    )
    for log in activity_logs:
        latest_order = Order.objects.filter(user=log.user).order_by('-created_at').first()
        log.last_order_status = latest_order.status if latest_order else "Browsing Only"

    today = datetime.today()
    revenue_data = defaultdict(int)
    for i in range(6, 0, -1):
        month = (today.month - i) % 12 or 12
        orders_in_month = Order.objects.filter(created_at__month=month)
        month_name = datetime(1900, month, 1).strftime('%b')
        revenue_data[month_name] = sum(o.total for o in orders_in_month if o.total)

    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:5]

    return render(request, "dashboard.html", {
        "products_count": products_count,
        "orders_count": orders_count,
        "users_count": users_count,
        "revenue": revenue,
        "recent_orders": recent_orders,
        "revenue_labels": list(revenue_data.keys()),
        "revenue_values": list(revenue_data.values()),
        "top_products_labels": [p.name for p in top_products],
        "top_products_values": [p.total_sold or 0 for p in top_products],
        "customer_activity": activity_logs,
        "products": Product.objects.all(),
    })


@staff_member_required
def customers(request):
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    return render(request, 'customers.html', {'orders': orders})


@staff_member_required
def activity_view(request):
    activity_logs = (
        UserActivity.objects.select_related('user', 'product').order_by('-timestamp')[:20]
    )
    for log in activity_logs:
        latest_order = Order.objects.filter(user=log.user).order_by('-created_at').first()
        log.last_order_status = latest_order.status if latest_order else "Browsing Only"
    return render(request, "activity.html", {"customer_activity": activity_logs})


@staff_member_required
def analytics_view(request):
    revenue_data = Order.objects.values('created_at__date').annotate(
        total_daily=Sum('total')
    ).order_by('created_at__date')

    product_data = (
        OrderItem.objects.values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    return render(request, 'analytics.html', {
        'revenue_labels': json.dumps([str(item['created_at__date']) for item in revenue_data]),
        'revenue_values': json.dumps([float(item['total_daily'] or 0) for item in revenue_data]),
        'top_products_labels': json.dumps([item['product__name'] for item in product_data]),
        'top_products_values': json.dumps([int(item['total_sold'] or 0) for item in product_data]),
    })


@staff_member_required
def settings_view(request):
    return render(request, "settings.html", {})


@staff_member_required
def manage_products(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'manage_products.html', {'products': products})


@staff_member_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('manage_products')


@staff_member_required
# ── REPLACE your existing manage_orders view with this ──

@staff_member_required
def manage_orders(request):
    orders = (
        Order.objects
        .select_related('user', 'user__profile')
        .prefetch_related('items', 'items__product', 'items__product__images')
        .order_by('-created_at')          # newest first
    )

    total_orders  = orders.count()
    pending_count = orders.filter(status__in=['Pending', 'STK_Sent']).count()
    paid_count    = orders.filter(status__in=['Paid', 'Delivered', 'Confirmed']).count()
    total_revenue = orders.aggregate(t=Sum('total'))['t'] or 0

    return render(request, 'manage_orders.html', {
        'orders'        : orders,
        'status_choices': Order.STATUS_CHOICES,
        'total_orders'  : total_orders,
        'pending_count' : pending_count,
        'paid_count'    : paid_count,
        'total_revenue' : total_revenue,
    })

@staff_member_required
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = request.POST.get('status')
    order.save()
    return redirect('manage_orders')


@staff_member_required
def update_price(request, pk):
    if request.method == "POST":
        product = get_object_or_404(Product, id=pk)
        new_price = request.POST.get("price")
        product.price = new_price
        product.save()
    return redirect('manage_products')


@staff_member_required
def mark_out_of_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.stock = 0
    product.save()
    return redirect('manage_products')


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
        specifications = request.POST.get("specifications")
        short_desc = request.POST.get('short_description')
        duration_val = request.POST.get("discount_duration_hours")

        if not brand_id:
            messages.error(request, "Please select a brand.")
            return redirect("add_product")

        brand = Brand.objects.get(id=brand_id)

        if new_category:
            category, _ = Category.objects.get_or_create(name=new_category)
        else:
            if not category_id:
                messages.error(request, "Please select or create a category.")
                return redirect("add_product")
            category = Category.objects.get(id=category_id)

        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            category=category,
            brand=brand,
            short_description=short_desc,
            specifications=specifications,
        )

        discount = float(discount_val) if discount_val else 0
        duration = int(duration_val) if duration_val and duration_val.isdigit() else 0

        product.discount = discount
        product.discount_duration_hours = duration

        if discount > 0 and duration > 0:
            product.discount_start_time = timezone.now()

        product.save()

        for img in request.FILES.getlist('images'):
            ProductImage.objects.create(product=product, image=img)

        messages.success(request, f"{product.name} added successfully!")
        return redirect("add_product")

    return render(request, "add_product.html", {"categories": categories, "brands": brands})


@staff_member_required
def most_purchased_products_view(request):
    products = Product.objects.annotate(
        buyers_count=Count('orderitem__order__user', distinct=True),
        total_sold=Sum('orderitem__quantity'),
    ).order_by('-total_sold')[:20]
    return render(request, 'admin/most_purchased_products.html', {'products': products})


@staff_member_required
@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your admin key has been updated successfully!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


@staff_member_required
@user_passes_test(lambda u: u.is_superuser)
def add_admin_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not username or not password:
            messages.error(request, "All fields are required!")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
        else:
            new_admin = User.objects.create_user(username=username, password=password)
            new_admin.is_staff = True
            new_admin.is_superuser = True
            new_admin.save()
            messages.success(request, f"Admin {username} created successfully!")
            return redirect('add_admin_view')

    return render(request, 'add_admin.html')


@staff_member_required
def delete_orders(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        Order.objects.filter(id__in=selected_ids).delete()
    return redirect('dashboard')


@staff_member_required
def delete_logs(request):
    if request.method == 'POST':
        log_ids = request.POST.getlist('selected_ids')
        UserActivity.objects.filter(id__in=log_ids).delete()
    return redirect('dashboard')


@staff_member_required
def bulk_delete_products(request):
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        if product_ids:
            Product.objects.filter(id__in=product_ids).delete()
    return redirect('manage_products')


@staff_member_required
def bulk_delete_orders(request):
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        if order_ids:
            Order.objects.filter(id__in=order_ids).delete()
    return redirect('customers')


# ═══════════════════════════════════════════════════════════
# M-PESA CALLBACK
# ═══════════════════════════════════════════════════════════

@csrf_exempt
def mpesa_callback(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        stk_callback = data['Body']['stkCallback']
        result_code = stk_callback['ResultCode']
        checkout_request_id = stk_callback['CheckoutRequestID']

        if result_code == 0:
            metadata = stk_callback['CallbackMetadata']['Item']
            mpesa_receipt = next(
                (item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber'),
                None
            )
            try:
                order = Order.objects.get(checkout_request_id=checkout_request_id)
                order.status = 'Paid'
                if mpesa_receipt:
                    order.mpesa_receipt = mpesa_receipt
                order.save()
                logger.info("M-Pesa payment confirmed for order %s | receipt %s", order.id, mpesa_receipt)
            except Order.DoesNotExist:
                logger.warning("M-Pesa callback: no order found for CheckoutRequestID %s", checkout_request_id)
        else:
            logger.warning("M-Pesa callback: non-zero result code %s for %s", result_code, checkout_request_id)

    except Exception:
        logger.exception("M-Pesa callback processing error")

    return HttpResponse(status=200)


def initiate_payment(request, order_id):
    order = Order.objects.get(id=order_id)
    response = lipa_na_mpesa(
        phone_number=order.phone,
        amount=int(order.total),
        account_ref=f"GSK{order.id}",
        transaction_desc="Gadget Purchase",
    )
    if response.get('ResponseCode') == '0':
        order.mpesa_checkout_id = response['CheckoutRequestID']
        order.save()
        return JsonResponse({'status': 'sent', 'message': 'Check your phone for the PIN prompt!'})
    logger.warning("STK push failed for order %s: %s", order_id, response)
    return JsonResponse({'status': 'error', 'message': 'Failed to trigger M-Pesa'})


# ═══════════════════════════════════════════════════════════
# SOKOBOT  (Gemini-powered chat)
# ═══════════════════════════════════════════════════════════

_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)


@csrf_exempt
def sokobot_chat(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({"reply": "Please type a message."})

        msg = user_message.lower()

        # Quick-reply shortcuts (no API quota used)
        if "location" in msg or "shop" in msg:
            return JsonResponse({"reply": "We are located at CBD, Laxmi Plaza Shop No. 5."})
        if "delivery" in msg:
            return JsonResponse({"reply": "We deliver across all 47 counties in Kenya."})
        if "payment" in msg or "mpesa" in msg:
            return JsonResponse({
                "reply": "We accept M-Pesa Till 5280343, bank transfer and pay on delivery within Nairobi."
            })

        prompt = (
            "You are SokoBot for Gadget Soko Kenya.\n"
            "Reply shortly and professionally.\n\n"
            f"Customer:\n{user_message}"
        )

        response = _gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return JsonResponse({"reply": response.text.strip()})

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            logger.warning("Gemini quota exceeded: %s", error_str)
            return JsonResponse({"reply": "SokoBot is busy right now. Please try again later."})
        logger.exception("SokoBot error")
        return JsonResponse({"reply": "Something went wrong."}, status=500)


# ═══════════════════════════════════════════════════════════
# SIGNALS
# ═══════════════════════════════════════════════════════════

@receiver(pre_save, sender=Brand)
def auto_assign_brand_logo(sender, instance, **kwargs):
    if not instance.logo and instance.name:
        brand_slug = slugify(instance.name)
        relative_path = f'brand_master_assets/{brand_slug}.png'
        absolute_path = os.path.join(settings.MEDIA_ROOT, 'brand_master_assets', f'{brand_slug}.png')

        if os.path.exists(absolute_path):
            instance.logo = relative_path
            logger.debug("Auto-assigned logo for brand '%s' → %s", instance.name, relative_path)
        else:
            logger.debug("No logo asset found for brand '%s' at %s", instance.name, absolute_path)

import logging
import threading
from itertools import islice

from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.core.mail import get_connection, EmailMultiAlternatives

from .models import Product

logger = logging.getLogger(__name__)
User = get_user_model()

# ── Tuneable constants ─────────────────────────────────────────────────────────
BATCH_SIZE   = 50   # recipients per SMTP transaction
MAX_WORKERS  = 4    # parallel threads (keep ≤ your SMTP provider's connection limit)
# ──────────────────────────────────────────────────────────────────────────────

@staff_member_required
def _chunked(iterable, size):
    """Yield successive chunks of `size` from any iterable."""
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

@staff_member_required
def _send_batch(subject, recipients, html, plain):
    """
    Open ONE SMTP connection and send to every address in `recipients`.
    Returns (sent_count, failed_count).
    """
    sent = failed = 0
    try:
        connection = get_connection()          # uses EMAIL_* settings
        connection.open()
        for email_addr in recipients:
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain,
                    from_email=None,           # falls back to DEFAULT_FROM_EMAIL
                    to=[email_addr],
                    connection=connection,     # ← reused connection, no re-handshake
                )
                msg.attach_alternative(html, "text/html")
                msg.send()
                sent += 1
            except Exception:
                failed += 1
                logger.exception("Email failed → %s", email_addr)
        connection.close()
    except Exception:
        logger.exception("Could not open SMTP connection for batch")
        failed += len(recipients)
    return sent, failed

@staff_member_required
def _blast_in_background(subject, all_emails, html, plain):
    """
    Split the full recipient list into BATCH_SIZE chunks and dispatch each
    chunk on its own thread (up to MAX_WORKERS threads at a time).

    Runs entirely outside the request/response cycle so Gunicorn never times out.
    """
    chunks = list(_chunked(all_emails, BATCH_SIZE))
    total_sent = total_failed = 0
    active_threads = []

    results = []   # thread-safe accumulator (one entry per chunk)

    def run_chunk(chunk, idx):
        s, f = _send_batch(subject, chunk, html, plain)
        results.append((s, f))
        logger.info("Chunk %d done — sent: %d  failed: %d", idx, s, f)

    for idx, chunk in enumerate(chunks):
        t = threading.Thread(target=run_chunk, args=(chunk, idx), daemon=True)
        active_threads.append(t)
        t.start()

        # Throttle: never exceed MAX_WORKERS concurrent threads
        if len(active_threads) >= MAX_WORKERS:
            for t in active_threads:
                t.join()
            active_threads = []

    # Wait for any remaining threads
    for t in active_threads:
        t.join()

    for s, f in results:
        total_sent   += s
        total_failed += f

    logger.info(
        "Marketing blast complete — sent: %d  failed: %d  subject: %s",
        total_sent, total_failed, subject,
    )
@staff_member_required

def market_product(request):
    products = Product.objects.all().order_by('-id')

    if request.method == "POST":
        subject      = request.POST.get("subject", "").strip()
        headline     = request.POST.get("headline", "").strip()
        body_message = request.POST.get("body_message", "").strip()
        cta_text     = request.POST.get("cta_text", "Shop Now").strip()
        cta_url      = request.POST.get("cta_url", "https://gadgetsoko.com").strip()
        product_ids  = request.POST.getlist("product_ids")

        if not subject or not headline:
            messages.error(request, "Subject and headline are required.")
            return redirect("market_product")

        users = User.objects.filter(
            is_active=True, email__isnull=False
        ).exclude(email="")

        if not users.exists():
            messages.error(request, "No registered customers found.")
            return redirect("market_product")

        # ── Protocol detection (Nginx reverse-proxy aware) ────────────────────
        forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO', '').strip()
        if forwarded_proto in ('https', 'http'):
            protocol = forwarded_proto
        elif request.is_secure():
            protocol = 'https'
        else:
            host = request.get_host()
            protocol = 'https' if any(
                d in host for d in ('gadgetsoko.com', 'onrender.com', 'vercel.app')
            ) else 'http'

        raw_host = request.get_host()
        domain   = raw_host.split(':')[0] if ':' in raw_host else raw_host
        base_url = f"{protocol}://{domain}"

        # ── Build product rows (unchanged from your original) ─────────────────
        selected_products = []
        if product_ids:
            selected_products = list(
                Product.objects.filter(id__in=product_ids).select_related('category')
            )

        rows_html = ""
        for product in selected_products:
            img_url = None
            try:
                first_pi = product.images.first()
                if first_pi and first_pi.image and first_pi.image.name:
                    img_url = base_url + first_pi.image.url
            except Exception:
                logger.warning("ProductImage resolve failed — product %s", product.id)
            if not img_url:
                try:
                    if product.image and product.image.name:
                        img_url = base_url + product.image.url
                except Exception:
                    logger.warning("Main image resolve failed — product %s", product.id)
            if not img_url:
                img_url = "https://via.placeholder.com/52x52?text=No+Image"

            try:
                product_url = base_url + product.get_absolute_url()
            except Exception:
                product_url = f"{base_url}/products/{product.id}/"

            try:
                category_name = product.category.name
            except Exception:
                category_name = "Uncategorized"

            try:
                has_discount = bool(
                    product.discount and product.discount > 0 and product.is_discount_active
                )
            except AttributeError:
                has_discount = bool(product.discount and product.discount > 0)

            try:
                final_price = product.final_price
            except AttributeError:
                final_price = product.price

            if has_discount:
                price_cell = (
                    f"<span style='text-decoration:line-through;color:#94a3b8;"
                    f"font-size:11px;'>KES {int(product.price):,}</span><br>"
                    f"<span style='color:#f4330c;font-weight:bold;'>"
                    f"KES {int(final_price):,}</span><br>"
                    f"<span style='background:#f4330c;color:white;padding:2px 6px;"
                    f"font-size:10px;border-radius:3px;'>"
                    f"{int(product.discount)}% OFF</span>"
                )
            else:
                price_cell = f"KES {int(final_price):,}"

            rows_html += (
                f"<tr style='background-color:#f8fafc;'>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;"
                f"vertical-align:middle;width:68px;'>"
                f"<a href='{product_url}'>"
                f"<img src='{img_url}' alt='' width='52' height='52' "
                f"style='border-radius:6px;object-fit:cover;display:block;"
                f"border:1px solid #e2e8f0;'></a></td>"
                f"<td style='padding:10px 14px;color:#1e293b;font-size:13px;"
                f"border-bottom:1px solid #e2e8f0;vertical-align:middle;'>"
                f"<a href='{product_url}' style='color:#0b3a63;font-weight:bold;"
                f"text-decoration:none;'>{product.name}</a><br>"
                f"<span style='color:#64748b;font-size:12px;'>{category_name}</span></td>"
                f"<td style='padding:10px 14px;font-size:13px;"
                f"border-bottom:1px solid #e2e8f0;text-align:right;"
                f"vertical-align:middle;'>{price_cell}</td>"
                f"</tr>"
            )

        products_html = ""
        if rows_html:
            products_html = f"""
            <tr>
              <td style="padding:0 20px 30px 20px;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%"
                       style="border-top:2px solid #f4330c;">
                  <tr style="background-color:#0b3a63;">
                    <td style="padding:10px;color:#fff;font-size:12px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;width:68px;">
                      Photo</td>
                    <td style="padding:10px 14px;color:#fff;font-size:12px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;">Product</td>
                    <td style="padding:10px 14px;color:#fff;font-size:12px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;text-align:right;">
                      Price</td>
                  </tr>
                  {rows_html}
                </table>
              </td>
            </tr>"""

        inner = f"""
        <tr>
          <td style="padding:50px 20px;text-align:center;">
            <h2 style="color:#0b3a63;font-size:24px;margin:0 0 10px 0;
                       font-weight:bold;text-transform:uppercase;letter-spacing:2px;">
              {headline}
            </h2>
            <p style="color:#1e293b;font-size:16px;line-height:26px;margin:0 0 35px 0;">
              {body_message}
            </p>
            <a href="{cta_url}"
               style="background-color:#f4330c;color:#ffffff;padding:18px 45px;
                      text-decoration:none;font-size:13px;font-weight:bold;
                      display:inline-block;text-transform:uppercase;letter-spacing:2px;">
              {cta_text}
            </a>
          </td>
        </tr>
        {products_html}"""

        html  = _email_wrapper(inner)
        plain = (
            f"{headline}\n\n{body_message}\n\n"
            + (
                "\n".join(
                    f"- {p.name} | KES {int(p.final_price):,}"
                    + (f" ({int(p.discount)}% OFF)" if p.discount and p.is_discount_active else "")
                    for p in selected_products
                ) + "\n\n"
                if selected_products else ""
            )
            + f"Shop now: {cta_url}"
        )

        # ── Collect all email addresses BEFORE spawning the thread ────────────
        # QuerySets are lazy; evaluate now so the thread never touches the DB
        # through a potentially-closed request context.
        all_emails = list(users.values_list('email', flat=True))
        recipient_count = len(all_emails)

        # ── Fire-and-forget: background thread — Gunicorn returns immediately ─
        t = threading.Thread(
            target=_blast_in_background,
            args=(subject, all_emails, html, plain),
            daemon=True,
        )
        t.start()

        messages.success(
            request,
            f"✅ Blast queued — sending to {recipient_count} customer(s) in the background. "
            f"Check django.log for delivery results.",
        )
        return redirect("market_product")

    # ── GET ───────────────────────────────────────────────────────────────────
    total_users = User.objects.filter(is_active=True).count()
    email_users = (
        User.objects.filter(is_active=True, email__isnull=False).exclude(email="").count()
    )
    return render(request, "market_product.html", {
        "products":    products,
        "total_users": total_users,
        "email_users": email_users,
    })
# ─────────────────────────────────────────────────────────────────
# ADD THESE VIEWS TO YOUR views.py
# Also add  UserProfile  to your .models import at the top:
#   from .models import (..., UserProfile)
# ─────────────────────────────────────────────────────────────────
import os
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

# Add UserProfile to your existing models import, e.g.:
# from .models import (..., UserProfile)

NAIROBI_AREAS = [
    "CBD - Town",
    "Westlands",
    "Eastlands",
    "Roysambu",
    "Langata",
    "Karen",
    "Kasarani",
    "Embakasi",
    "Kibera",
    "Dagoretti",
    "Ruaraka",
    "Makadara",
    "Pumwani",
]


@login_required
def edit_profile(request):
    """Full profile-edit view: avatar, name, username, email, phone,
       location (mirrors checkout), password change, account deletion."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── 1. Save profile details ──────────────────────────────
        if action == 'save_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name', '').strip()
            new_username = request.POST.get('username', '').strip()
            new_email  = request.POST.get('email', '').strip()
            phone      = request.POST.get('phone', '').strip()
            region     = request.POST.get('region', 'nairobi')
            nairobi_area     = request.POST.get('nairobi_area', '').strip()
            upcountry_county = request.POST.get('upcountry_county', '').strip()
            upcountry_town   = request.POST.get('upcountry_town', '').strip()
            address_notes    = request.POST.get('address_notes', '').strip()

            # Avatar upload
            if 'avatar' in request.FILES:
                # Delete old file to save storage
                if profile.avatar and profile.avatar.name:
                    try:
                        old_path = profile.avatar.path
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception:
                        pass
                profile.avatar = request.FILES['avatar']

            # Username uniqueness check
            if new_username and new_username != request.user.username:
                if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                    messages.error(request, "That username is already taken.")
                    return redirect('edit_profile')
                request.user.username = new_username

            # Email uniqueness check
            if new_email and new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    messages.error(request, "An account with that email already exists.")
                    return redirect('edit_profile')
                request.user.email = new_email

            request.user.first_name = first_name
            request.user.last_name  = last_name
            request.user.save()

            profile.phone            = phone
            profile.region           = region
            profile.nairobi_area     = nairobi_area
            profile.upcountry_county = upcountry_county
            profile.upcountry_town   = upcountry_town
            profile.address_notes    = address_notes
            profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect('edit_profile')

        # ── 2. Change password ───────────────────────────────────
        elif action == 'change_password':
            old_pw  = request.POST.get('old_password', '')
            new_pw  = request.POST.get('new_password1', '')
            new_pw2 = request.POST.get('new_password2', '')

            if not request.user.check_password(old_pw):
                messages.error(request, "Current password is incorrect.")
            elif new_pw != new_pw2:
                messages.error(request, "New passwords do not match.")
            elif len(new_pw) < 6:
                messages.error(request, "Password must be at least 6 characters.")
            else:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)   # keep session alive
                messages.success(request, "Password changed successfully!")
            return redirect('edit_profile')

        # ── 3. Delete account ────────────────────────────────────
        elif action == 'delete_account':
            confirm = request.POST.get('confirm_delete', '').strip()
            if confirm != request.user.username:
                messages.error(request, "Username did not match. Account not deleted.")
                return redirect('edit_profile')
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Your account has been permanently deleted.")
            return redirect('index')

    return render(request, 'edit_profile.html', {
        'profile': profile,
        'nairobi_areas': NAIROBI_AREAS,
    })


@login_required
def check_username(request):
    """AJAX endpoint — returns {available: true/false}"""
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'message': 'Enter a username'})
    if username == request.user.username:
        return JsonResponse({'available': True, 'message': 'That is your current username'})
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({
        'available': not exists,
        'message': 'Available!' if not exists else 'Already taken',
    })


# views.py  — add this view (or merge into your existing admin views file)

from django.contrib.auth.models    import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator          import Paginator
from django.utils                   import timezone
from django.shortcuts               import render, get_object_or_404

from .models import Order   # adjust import to your app name


def admin_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_staff)(view_func))


@admin_required
def customers(request):
    qs = (
        User.objects
        .filter(is_staff=False)
        .select_related('profile')
        .prefetch_related('order_set')
        .order_by('-date_joined')
    )

    # ── Stats ──────────────────────────────────────────────
    total_customers      = qs.count()
    customers_with_orders = qs.filter(order__isnull=False).distinct().count()

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = qs.filter(date_joined__gte=month_start).count()

    # ── Pagination ─────────────────────────────────────────
    paginator  = Paginator(qs, 20)          # 20 per page
    page_num   = request.GET.get('page', 1)
    customers_page = paginator.get_page(page_num)

    return render(request, 'customers.html', {
        'customers'            : customers_page,
        'total_customers'      : total_customers,
        'customers_with_orders': customers_with_orders,
        'new_this_month'       : new_this_month,
    })


@admin_required
def customer_detail(request, pk):
    """Optional detail view — link from the eye icon."""
    customer = get_object_or_404(
        User.objects.select_related('profile').prefetch_related('order_set'),
        pk=pk, is_staff=False
    )
    orders = customer.order_set.order_by('-created_at')

    return render(request, 'customer_detail.html', {
        'customer': customer,
        'orders'  : orders,
    })


# ─────────────────────────────────────────────────────────────────
# ADD TO urls.py:
#   path('admin/customers/<int:pk>/',       customer_detail,     name='customer_detail'),
#   path('admin/customers/<int:pk>/email/', send_customer_email, name='send_customer_email'),
#
# REPLACE your existing update_order_status with the one at the bottom.
# ─────────────────────────────────────────────────────────────────

from django.db.models import Sum

@staff_member_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        User.objects.select_related('profile')
                    .prefetch_related('order_set__items__product__images'),
        pk=pk
    )

    orders = customer.order_set.prefetch_related(
        'items', 'items__product', 'items__product__images'
    ).order_by('-created_at')

    total_spent = orders.aggregate(t=Sum('total'))['t'] or 0
    status_choices = Order.STATUS_CHOICES

    return render(request, 'customer_detail.html', {
        'customer': customer,
        'orders': orders,
        'total_spent': total_spent,
        'status_choices': status_choices,
    })


@staff_member_required
def send_customer_email(request, pk):
    customer = get_object_or_404(User, pk=pk)

    if request.method != 'POST':
        return redirect('customer_detail', pk=pk)

    if not customer.email:
        messages.error(request, "This customer has no email address on file.")
        return redirect('customer_detail', pk=pk)

    subject     = request.POST.get('subject', '').strip()
    message_txt = request.POST.get('message', '').strip()
    cta_text    = request.POST.get('cta_text', '').strip()
    cta_url     = request.POST.get('cta_url', '').strip()
    product_ids = request.POST.getlist('product_ids')

    if not subject or not message_txt:
        messages.error(request, "Subject and message are required.")
        return redirect('customer_detail', pk=pk)

    protocol = 'https'
    domain   = getattr(settings, 'SITE_DOMAIN', 'gadgetsoko.com')
    base_url = f"{protocol}://{domain}"

    # ── Build product rows ──
    rows_html = ""
    if product_ids:
        selected = Product.objects.filter(
            id__in=product_ids
        ).select_related('category').prefetch_related('images')

        for product in selected:
            img_url = None
            try:
                pi = product.images.first()
                if pi and pi.image and pi.image.name:
                    img_url = base_url + pi.image.url
            except Exception:
                pass
            if not img_url:
                try:
                    if product.image and product.image.name:
                        img_url = base_url + product.image.url
                except Exception:
                    pass
            if not img_url:
                img_url = "https://via.placeholder.com/52x52?text=No+Image"

            try:
                product_url = base_url + product.get_absolute_url()
            except Exception:
                product_url = f"{base_url}/products/{product.id}/"

            try:
                category_name = product.category.name
            except Exception:
                category_name = ""

            try:
                final_price = product.final_price
            except Exception:
                final_price = product.price

            rows_html += (
                f"<tr style='background:#f8fafc;'>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;"
                f"width:68px;vertical-align:middle;'>"
                f"<a href='{product_url}'>"
                f"<img src='{img_url}' width='52' height='52' "
                f"style='object-fit:cover;border:1px solid #e2e8f0;display:block;'>"
                f"</a></td>"
                f"<td style='padding:10px 14px;font-size:13px;"
                f"border-bottom:1px solid #e2e8f0;vertical-align:middle;'>"
                f"<a href='{product_url}' style='color:#0b3a63;font-weight:bold;"
                f"text-decoration:none;'>{product.name}</a><br>"
                f"<span style='color:#64748b;font-size:12px;'>{category_name}</span></td>"
                f"<td style='padding:10px 14px;font-size:13px;font-weight:700;"
                f"border-bottom:1px solid #e2e8f0;text-align:right;vertical-align:middle;'>"
                f"KES {int(final_price):,}</td>"
                f"</tr>"
            )

    products_table = ""
    if rows_html:
        products_table = f"""
        <tr>
          <td style="padding:0 20px 30px 20px;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="border-top:2px solid #f4330c;">
              <tr style="background:#0b3a63;">
                <td style="padding:10px;color:#fff;font-size:12px;font-weight:bold;
                           text-transform:uppercase;letter-spacing:1px;width:68px;">Photo</td>
                <td style="padding:10px 14px;color:#fff;font-size:12px;font-weight:bold;
                           text-transform:uppercase;letter-spacing:1px;">Product</td>
                <td style="padding:10px 14px;color:#fff;font-size:12px;font-weight:bold;
                           text-transform:uppercase;letter-spacing:1px;text-align:right;">Price</td>
              </tr>
              {rows_html}
            </table>
          </td>
        </tr>"""

    # ── CTA ──
    cta_html = ""
    if cta_text and cta_url:
        cta_html = (
            f'<a href="{cta_url}" '
            f'style="background:#f4330c;color:#fff;padding:16px 42px;'
            f'text-decoration:none;font-size:13px;font-weight:bold;'
            f'display:inline-block;text-transform:uppercase;letter-spacing:2px;">'
            f'{cta_text}</a>'
        )

    display_name = customer.get_full_name() or customer.username

    inner = f"""
    <tr>
      <td style="padding:40px 20px;text-align:center;">
        <h2 style="color:#0b3a63;font-size:22px;margin:0 0 8px 0;
                   font-weight:bold;text-transform:uppercase;letter-spacing:2px;">
          Hi, {display_name}
        </h2>
        <p style="color:#1e293b;font-size:15px;line-height:26px;margin:0 0 28px 0;
                  text-align:left;white-space:pre-line;">
          {message_txt}
        </p>
        {cta_html}
      </td>
    </tr>
    {products_table}"""

    html  = _email_wrapper(inner)
    plain = f"Hi {display_name},\n\n{message_txt}"
    if cta_text and cta_url:
        plain += f"\n\n{cta_text}: {cta_url}"

    _send_html_email(subject, customer.email, html, plain)
    messages.success(request, f"Email sent to {customer.email} ✓")
    return redirect('customer_detail', pk=pk)


# ── REPLACE your existing update_order_status with this ──
# The only change: reads a hidden 'next' field so saves from the
# detail page return back there instead of manage_orders.

@staff_member_required
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = request.POST.get('status', order.status)
    order.save()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('manage_orders')


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

@login_required
def my_orders(request):
    """Customer-facing order history page."""
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    # Count orders that are still "active" (not delivered, not cancelled)
    active_count = orders.exclude(status__in=['Delivered', 'Cancelled']).count()
    return render(request, 'my_orders.html', {
        'orders': orders,
        'active_count': active_count,
    })


@login_required
def cancel_order(request, order_id):
    """Customer can cancel only if status hasn't reached Shipped."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    CANCELLABLE = {'Pending', 'STK_Sent', 'Paid', 'Processing'}
    if order.status in CANCELLABLE:
        order.status = 'Cancelled'
        order.save()
        messages.success(request, f"Order #{order.id} has been cancelled.")
    else:
        messages.error(request, "This order can no longer be cancelled.")
    return redirect('my_orders')


from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.shortcuts import redirect
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

@csrf_exempt
def google_onetap_callback(request):
    if request.method == 'POST':
        credential = request.POST.get('credential')
        if credential:
            try:
                idinfo = id_token.verify_oauth2_token(
                    credential,
                    google_requests.Request(),
                    settings.GOOGLE_CLIENT_ID
                )
                email = idinfo.get('email')
                from django.contrib.auth.models import User
                from allauth.socialaccount.models import SocialAccount
                try:
                    social = SocialAccount.objects.get(
                        provider='google', uid=idinfo['sub']
                    )
                    user = social.user
                except SocialAccount.DoesNotExist:
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={'username': email.split('@')[0]}
                    )
                    if created:
                        SocialAccount.objects.create(
                            user=user, provider='google', uid=idinfo['sub']
                        )
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                return redirect('index')
            except Exception:
                pass
    return redirect('userlog')