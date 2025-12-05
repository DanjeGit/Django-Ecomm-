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
        # 2. Pass parameters separately to avoid URL encoding issues
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
    # 1. Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 2. HARDCODE these values for Sandbox (Do not use settings.py )
    shortcode = "174379"
    passkey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
    
    # 3. Generate the password
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

    # Inside stk_push function...
    payload = {
        "BusinessShortCode": 174379, # Hardcoded
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(float(amount)),
        "PartyA": formatted_phone,
        "PartyB": 174379,            # Hardcoded (Must match BusinessShortCode)
        "PhoneNumber": formatted_phone,
        "CallBackURL": settings.CALLBACK_URL, # Keep your ngrok URL here
        "AccountReference": "DjangoTest",
        "TransactionDesc": "Payment"
    }

    # try:
    #     response = requests.post(api_url, json=payload, headers=headers)
    #     # Always log response details to help diagnose 400/500s
    #     try:
    #         resp_json = response.json()
    #     except Exception:
    #         resp_json = None

    #     if response.status_code >= 400:
    #         print("STK Push Error:")
    #         print("Status:", response.status_code)
    #         print("Body (text):", response.text)
    #         if resp_json:
    #             print("Body (json):", json.dumps(resp_json, indent=2))
    #         return {"error": "STK push failed", "status": response.status_code, "body": resp_json or response.text}

    #     return resp_json or {"raw": response.text}

    # except requests.exceptions.RequestException as e:
    #     print(f"Request Error: {e}")
    #     return {"error": str(e)}
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        # --- THIS IS THE FIX ---
        # Print the exact message from Safaricom (e.g., "Invalid Account Reference")
        print("ERROR RESPONSE FROM SAFARICOM:")
        print(response.text) 
        return {"error": response.text} # Send this to your frontend so you can see it
        
    except Exception as e:
        print(f"General Error: {e}")
        return {"error": str(e)}