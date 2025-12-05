import os
from dotenv import load_dotenv
import requests
# Load .env file from current directory
from requests.auth import HTTPBasicAuth
load_dotenv(dotenv_path=r"C:\Users\DANNY\Desktop\eMobilis FP\resource_loop\.env")

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')

# Optional: fallbacks or validation
if not CONSUMER_KEY or not CONSUMER_SECRET:
    raise RuntimeError("Missing CONSUMER_KEY or CONSUMER_SECRET in .env")

print("Key loaded:", bool(CONSUMER_KEY))

def test_connection_robust():
    # 1. Base URL without the '?' part
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    
    # 2. Pass parameters separately so Python formats them perfectly
    params = {"grant_type": "client_credentials"}
    
    print(f"Testing connection...")
    print(f"Key Length: {len(CONSUMER_KEY)} | Secret Length: {len(CONSUMER_SECRET)}")

    try:
        response = requests.get(
            url, 
            params=params,  # This fixes the 400 Error
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=10 # Add timeout to prevent hanging
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Token received:")
            print(response.json().get("access_token"))
        else:
            print("\n❌ FAILED")
            print("Response Body:", response.text)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    test_connection_robust()