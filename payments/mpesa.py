import requests
import json
import base64
from datetime import datetime
from django.conf import settings


def get_access_token():
    """Get OAuth access token from M-Pesa API"""
    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    if getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox') == 'production':
        api_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    try:
        response = requests.get(
            api_url,
            auth=requests.auth.HTTPBasicAuth(
                settings.MPESA_CONSUMER_KEY, 
                settings.MPESA_CONSUMER_SECRET
            ),
            timeout=30
        )
        
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"✅ M-Pesa Access Token obtained successfully")
            return token
        else:
            print(f"❌ Failed to get access token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ M-Pesa get_access_token error: {e}")
        return None


def stk_push(amount, phone_number, account_reference, transaction_desc, callback_url):
    """
    Initiate STK push for payment
    """
    access_token = get_access_token()
    
    if not access_token:
        return {'success': False, 'error': 'Failed to get access token'}
    
    # Format phone number (remove leading 0 or +254)
    original_phone = phone_number
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    # Remove any non-digit characters
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    print(f"📱 Formatted phone number: {original_phone} -> {phone_number}")
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Generate password
    shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
    passkey = getattr(settings, 'MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    
    password_str = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode('utf-8')
    
    api_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    if getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox') == 'production':
        api_url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'BusinessShortCode': shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': str(int(amount)),
        'PartyA': phone_number,
        'PartyB': shortcode,
        'PhoneNumber': phone_number,
        'CallBackURL': callback_url,
        'AccountReference': account_reference[:12],
        'TransactionDesc': transaction_desc[:13]
    }
    
    print(f"📤 Sending STK push request to M-Pesa...")
    print(f"   Amount: KES {amount}")
    print(f"   Phone: {phone_number}")
    print(f"   Account Ref: {account_reference[:12]}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        print(f"📥 M-Pesa Response: {result}")
        
        if result.get('ResponseCode') == '0':
            return {
                'success': True,
                'checkout_request_id': result.get('CheckoutRequestID'),
                'merchant_request_id': result.get('MerchantRequestID'),
                'response_code': result.get('ResponseCode'),
                'response_description': result.get('ResponseDescription')
            }
        else:
            return {
                'success': False, 
                'error': result.get('errorMessage', 'STK push failed'),
                'response_code': result.get('ResponseCode')
            }
    except Exception as e:
        print(f"❌ STK push exception: {e}")
        return {'success': False, 'error': str(e)}


def query_status(checkout_request_id):
    """Query transaction status"""
    access_token = get_access_token()
    
    if not access_token:
        return {'success': False, 'error': 'Failed to get access token'}
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
    passkey = getattr(settings, 'MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    
    password_str = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode('utf-8')
    
    api_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    if getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox') == 'production':
        api_url = 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'BusinessShortCode': shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        print(f"📥 Query Status Response: {result}")
        
        if result.get('ResultCode') == '0':
            return {
                'success': True, 
                'status': 'completed',
                'result_code': result.get('ResultCode'),
                'result_desc': result.get('ResultDesc')
            }
        elif result.get('ResultCode') == '1037':
            return {
                'success': False, 
                'status': 'cancelled',
                'error': 'User cancelled the transaction'
            }
        else:
            return {
                'success': False, 
                'status': 'pending',
                'result_code': result.get('ResultCode'),
                'error': result.get('ResultDesc', 'Transaction pending')
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}