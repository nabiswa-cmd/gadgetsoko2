from django.core.mail import send_mail
from django.conf import settings

def send_order_email(order):
    subject = f"Order Confirmation - #{order.id}"

    message = f"""
Hello {order.customer_name},

Your order has been successfully placed.

Order ID: {order.id}
Amount Paid: {order.total_amount}
Date: {order.created_at}
Status: {order.status}

Thank you for shopping with us.
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [order.customer_email],
        fail_silently=False,
    )

import requests
from django.conf import settings

def lipa_na_mpesa(phone_number, amount, account_ref, transaction_desc):
    """
    Handles the STK Push request to Safaricom Daraja API.
    """
    # For now, we return a mock failed response so the app doesn't crash
    # Once you have your Daraja keys, you will put the real API logic here.
    print(f"Attempting STK Push to {phone_number} for KES {amount}")
    
    # Mock response structure that matches what your view expects
    return {
        'ResponseCode': '1', 
        'CheckoutRequestID': None,
        'CustomerMessage': 'API Not Configured'
    }