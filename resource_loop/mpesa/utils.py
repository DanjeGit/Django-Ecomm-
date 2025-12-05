import base64
import requests
import json
from datetime import datetime
from requests.auth import HTTPBasicAuth
from django.conf import settings

# utils.py (Partial update)

def get_access_token():
    consumer_key = settings.CONSUMER_KEY
    consumer_secret = settings.CONSUMER_SECRET
    
    # 1. Use the clean URL (no ?grant_type=... here)
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    
    try:
        # 2. Pass parameters separately (This fixed your 400 Error)
        response = requests.get(
            api_url, 
            params={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(consumer_key, consumer_secret)
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"Error generating token: {str(e)}")
        return None

def format_phone_number(phone):
    """Ensures phone number is in 2547XXXXXXXX format."""
    phone = str(phone).strip()
    if phone.startswith("+254"):
        return phone[1:]
    elif phone.startswith("0"):
        return "254" + phone[1:]
    return phone

def generate_password():
    """Generates the password and timestamp required for STK push."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = settings.SHORTCODE
    passkey = settings.PASSKEY
    
    data_to_encode = shortcode + passkey + timestamp
    encoded_string = base64.b64encode(data_to_encode.encode()).decode()
    return encoded_string, timestamp

def stk_push(amount, phone):
    """Initiates the STK Push request."""
    token = get_access_token()
    
    if not token:
        return {"error": "Failed to retrieve access token", "status": 500}

    password, timestamp = generate_password()
    formatted_phone = format_phone_number(phone)

    # --- CRITICAL FIX: This is the correct STK Push URL ---
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {token}",  # Fixed: using variable 'token', not function
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": settings.SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(float(amount)), # Ensure amount is an integer
        "PartyA": formatted_phone,
        "PartyB": settings.SHORTCODE,
        "PhoneNumber": formatted_phone,
        "CallBackURL": settings.CALLBACK_URL,
        "AccountReference": "DjangoTest",
        "TransactionDesc": "Payment via Django"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.JSONDecodeError:
        # This catches the specific error you were getting
        print("M-Pesa API Error (Non-JSON response):", response.text)
        return {"error": "M-Pesa API returned invalid data (likely HTML)", "raw": response.text}
        
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return {"error": str(e)}