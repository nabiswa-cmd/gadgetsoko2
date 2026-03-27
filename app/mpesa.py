import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from dotenv import load_dotenv
import base64
from datetime import datetime
import os
load_dotenv()

def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(
            os.getenv("MPESA_CONSUMER_KEY"),
            os.getenv("MPESA_CONSUMER_SECRET")
        )
    )

    print("TOKEN STATUS:", response.status_code)
    print("TOKEN RESPONSE:", response.text)

    try:
        data = response.json()
        return data.get('access_token')
    except ValueError:
        return None
def lipa_na_mpesa(phone_number, amount, account_ref, transaction_desc):
    token = get_mpesa_access_token()

    if not token:
        return {"error": "Failed to generate access token"}

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_str = f"{os.getenv("MPESA_SHORTCODE")}{os.getenv("MPESA_PASSKEY")}{timestamp}"
    password = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')

    payload = {
        "BusinessShortCode": os.getenv("MPESA_SHORTCODE"),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": os.getenv("MPESA_SHORTCODE"),
        "PhoneNumber": phone_number,
        "CallBackURL": os.getenv('MPESA_CALLBACK_URL'),
        "AccountReference": account_ref,
        "TransactionDesc": transaction_desc
    }

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print("STATUS CODE:", response.status_code)
    print("RAW RESPONSE:", response.text)

    try:
        return response.json()
    except ValueError:
        return {
            "error": "Invalid JSON response",
            "status_code": response.status_code,
            "raw_response": response.text
        }