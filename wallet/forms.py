from django import forms
from decimal import Decimal

class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('10'))
    payment_method = forms.ChoiceField(choices=[
        ('binance', 'Binance Pay'),
        ('okx', 'OKX Pay'),
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
    ])
    
    # Crypto fields
    wallet_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'USDT Wallet Address'}))
    
    # PayPal fields
    paypal_email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'paypal@email.com'}))
    
    # M-Pesa fields
    mpesa_phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': '07XXXXXXXX'}))
    
    # Bank fields
    bank_name = forms.CharField(required=False)
    bank_account_name = forms.CharField(required=False)
    bank_account_number = forms.CharField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        if payment_method == 'binance' and not cleaned_data.get('wallet_address'):
            raise forms.ValidationError('Wallet address is required for crypto withdrawal')
        if payment_method == 'paypal' and not cleaned_data.get('paypal_email'):
            raise forms.ValidationError('PayPal email is required')
        if payment_method == 'mpesa' and not cleaned_data.get('mpesa_phone'):
            raise forms.ValidationError('M-Pesa phone number is required')
        if payment_method == 'bank':
            if not cleaned_data.get('bank_name'):
                raise forms.ValidationError('Bank name is required')
            if not cleaned_data.get('bank_account_name'):
                raise forms.ValidationError('Account name is required')
            if not cleaned_data.get('bank_account_number'):
                raise forms.ValidationError('Account number is required')
        
        return cleaned_data