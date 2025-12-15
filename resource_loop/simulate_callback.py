import os
import django
import json
import requests
import sys

# Setup Django environment
# This allows us to access the database models directly
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resource_loop.settings')
django.setup()

from marketplace.models import Transaction

def simulate_success():
    print("--- M-Pesa Callback Simulator ---")
    
    # 1. Find the most recent pending transaction
    # We assume the user just tried to pay and it's waiting
    tx = Transaction.objects.filter(state='pending').order_by('-created_at').first()
    
    if not tx:
        print("❌ No pending transactions found in the database.")
        print("   Please initiate a payment first (even if it fails on the phone).")
        return

    if not tx.checkout_request_id:
        print(f"❌ Transaction #{tx.id} exists but has no CheckoutRequestID.")
        return

    print(f"✅ Found Pending Transaction #{tx.id}")
    print(f"   User: {tx.user.username}")
    print(f"   Amount: {tx.amount}")
    print(f"   Phone: {tx.phone_number}")
    print(f"   CheckoutRequestID: {tx.checkout_request_id}")
    print("-" * 40)

    # 2. Construct the Success Payload
    # This mimics exactly what Safaricom sends to your endpoint
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": tx.merchant_request_id or "TEST-MERCHANT-ID",
                "CheckoutRequestID": tx.checkout_request_id,
                "ResultCode": 0,  # 0 means Success
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {
                            "Name": "Amount",
                            "Value": float(tx.amount)
                        },
                        {
                            "Name": "MpesaReceiptNumber",
                            "Value": "SIMULATED123"
                        },
                        {
                            "Name": "TransactionDate",
                            "Value": 20251209120000
                        },
                        {
                            "Name": "PhoneNumber",
                            "Value": int(tx.phone_number) if tx.phone_number.isdigit() else 254700000000
                        }
                    ]
                }
            }
        }
    }

    # 3. Send the POST request to your local Django server
    url = "http://127.0.0.1:8000/mpesa/callback/"
    print(f"🚀 Sending simulated callback to: {url}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! The transaction should now be 'confirmed' and the order 'confirmed'.")
            print("   Check your dashboard or the admin panel.")
        else:
            print("\n❌ FAILED. Check the server logs for errors.")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ CONNECTION ERROR: Could not connect to localhost:8000.")
        print("   Is your Django server running? (python manage.py runserver)")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    simulate_success()
