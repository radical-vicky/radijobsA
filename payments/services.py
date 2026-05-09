import hashlib
import hmac
import json
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail

class BinancePayService:
    """Binance Pay integration service"""
    
    def __init__(self):
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        self.base_url = "https://api.binance.com" if not settings.DEBUG else "https://testnet.binance.com"
    
    def create_order(self, amount, currency='USDT', order_id=None):
        """Create a Binance Pay order"""
        import uuid
        if not order_id:
            order_id = str(uuid.uuid4())
        
        payload = {
            "env": {
                "terminalType": "WEB"
            },
            "merchantTradeNo": order_id,
            "orderAmount": str(amount),
            "currency": currency,
            "description": "RadiloxRemoteJobs Subscription",
            "returnUrl": "https://yourdomain.com/payments/binance/return/",
            "webhookUrl": "https://yourdomain.com/payments/webhook/binance/"
        }
        
        headers = self._get_headers(payload)
        response = requests.post(
            f"{self.base_url}/binancepay/openapi/v2/order",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'SUCCESS':
                return {
                    'success': True,
                    'checkout_url': data['data']['checkoutUrl'],
                    'prepay_id': data['data']['prepayId'],
                    'order_id': order_id
                }
        
        return {'success': False, 'error': response.text}
    
    def _get_headers(self, payload):
        """Generate Binance Pay headers with signature"""
        payload_str = json.dumps(payload)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return {
            'Content-Type': 'application/json',
            'BinancePay-Timestamp': str(int(timezone.now().timestamp() * 1000)),
            'BinancePay-Nonce': self._generate_nonce(),
            'BinancePay-Certificate-SN': self.api_key,
            'BinancePay-Signature': signature
        }
    
    def _generate_nonce(self):
        import secrets
        return secrets.token_hex(16)

class PayPalService:
    """PayPal integration service"""
    
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.mode = settings.PAYPAL_MODE
        self.base_url = "https://api-m.paypal.com" if self.mode == 'live' else "https://api-m.sandbox.paypal.com"
        self.access_token = None
    
    def get_access_token(self):
        """Get PayPal access token"""
        if self.access_token:
            return self.access_token
        
        auth = (self.client_id, self.client_secret)
        headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
        data = {'grant_type': 'client_credentials'}
        
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=auth,
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            return self.access_token
        
        raise Exception(f"Failed to get PayPal token: {response.text}")
    
    def create_order(self, amount, currency='USD', return_url=None):
        """Create a PayPal order"""
        access_token = self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency,
                    'value': str(amount)
                },
                'description': 'RadiloxRemoteJobs Subscription'
            }],
            'payment_source': {
                'paypal': {
                    'experience_context': {
                        'return_url': return_url or 'https://yourdomain.com/payments/paypal/return/',
                        'cancel_url': 'https://yourdomain.com/payments/paypal/cancel/'
                    }
                }
            }
        }
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 201:
            data = response.json()
            approval_url = next(link['href'] for link in data['links'] if link['rel'] == 'approve')
            return {
                'success': True,
                'order_id': data['id'],
                'approval_url': approval_url
            }
        
        return {'success': False, 'error': response.text}
    
    def capture_order(self, order_id):
        """Capture an approved PayPal order"""
        access_token = self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers=headers
        )
        
        if response.status_code == 201:
            return {'success': True, 'data': response.json()}
        
        return {'success': False, 'error': response.text}

class MpesaService:
    """M-Pesa integration service (Safaricom)"""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.environment = settings.MPESA_ENVIRONMENT
        self.base_url = "https://api.safaricom.co.ke" if self.environment == 'production' else "https://sandbox.safaricom.co.ke"
        self.access_token = None
    
    def get_access_token(self):
        """Get M-Pesa access token"""
        if self.access_token:
            return self.access_token
        
        auth = (self.consumer_key, self.consumer_secret)
        
        response = requests.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            auth=auth
        )
        
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            return self.access_token
        
        raise Exception(f"Failed to get M-Pesa token: {response.text}")
    
    def stk_push(self, amount, phone_number, account_reference, transaction_desc, callback_url):
        """Initiate STK Push for payment"""
        import datetime
        
        access_token = self.get_access_token()
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (self.shortcode + self.passkey + timestamp).encode()
        ).decode()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': amount,
            'PartyA': phone_number,
            'PartyB': self.shortcode,
            'PhoneNumber': phone_number,
            'CallBackURL': callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        response = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['ResponseCode'] == '0':
                return {
                    'success': True,
                    'checkout_request_id': data['CheckoutRequestID'],
                    'merchant_request_id': data['MerchantRequestID']
                }
        
        return {'success': False, 'error': response.text}
    
    def query_status(self, checkout_request_id):
        """Query STK Push status"""
        access_token = self.get_access_token()
        
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (self.shortcode + self.passkey + timestamp).encode()
        ).decode()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        response = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            headers=headers,
            json=payload
        )
        
        return response.json()

# Import base64 for M-Pesa
import base64

# Initialize services
binance_pay = BinancePayService()
paypal = PayPalService()
mpesa = MpesaService()