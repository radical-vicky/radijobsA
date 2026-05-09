from django import forms

class PaymentMethodForm(forms.Form):
    PAYMENT_METHODS = [
        ('binance', 'Binance Pay (Crypto USDT)'),
        ('okx', 'OKX Pay (Crypto USDT)'),
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa (Kenya)'),
        ('bank', 'Bank Transfer'),
    ]
    
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, widget=forms.RadioSelect)
    
    # Crypto fields
    crypto_currency = forms.ChoiceField(choices=[('USDT', 'USDT'), ('USDC', 'USDC')], required=False)
    
    # M-Pesa field
    mpesa_phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': '07XXXXXXXX'}))
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        mpesa_phone = cleaned_data.get('mpesa_phone')
        
        if payment_method == 'mpesa' and not mpesa_phone:
            raise forms.ValidationError('M-Pesa phone number is required')
        
        return cleaned_data