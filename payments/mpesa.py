import requests
import base64
from datetime import datetime
from django.conf import settings


class MpesaClient:
    def __init__(self, consumer_key, consumer_secret, passkey, shortcode):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.passkey = passkey
        self.shortcode = shortcode
        self.base_url = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENVIRONMENT == 'sandbox' else "https://api.safaricom.co.ke"
        self.access_token = None
    
    def get_access_token(self):
        """Get M-Pesa API access token"""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            self.access_token = result.get('access_token')
            return self.access_token
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push to customer's phone"""
        if not self.access_token:
            self.get_access_token()
        
        if not self.access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        # Format phone number (remove leading 0 or +254)
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'CheckoutRequestID': result.get('CheckoutRequestID'),
                    'message': 'STK push sent successfully'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('ResponseDescription', 'Unknown error')
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_transaction_status(self, checkout_request_id):
        """Check status of a transaction"""
        if not self.access_token:
            self.get_access_token()
        
        if not self.access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ResultCode') == '0':
                return {
                    'success': True,
                    'status': 'completed',
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'status': 'failed',
                    'error': result.get('ResultDesc', 'Transaction failed')
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}