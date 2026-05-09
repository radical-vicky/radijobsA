from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User, UserPaymentMethod


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'avatar': forms.FileInput(attrs={'class': 'form-input'}),
        }


class UserPaymentMethodForm(forms.ModelForm):
    """Form for adding/editing payment methods"""
    
    class Meta:
        model = UserPaymentMethod
        fields = ['payment_type', 'last_four', 'is_default', 
                  'card_holder_name', 'expiry_month', 'expiry_year',
                  'account_email', 'phone_number']
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-input'}),
            'last_four': forms.TextInput(attrs={'class': 'form-input', 'max_length': 4, 'placeholder': 'Last 4 digits'}),
            'card_holder_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Name on card'}),
            'expiry_month': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'MM'}),
            'expiry_year': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'YYYY'}),
            'account_email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@example.com'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+1234567890'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields optional based on payment type (handled in clean method if needed)
        self.fields['last_four'].required = True
        self.fields['is_default'].required = False


class CustomSignupForm(forms.ModelForm):
    """Custom signup form with role selection"""
    
    ROLE_CHOICES = (
        ('applicant', 'Job Applicant - Find and apply for jobs'),
        ('freelancer', 'Freelancer - Complete tasks and earn money'),
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="I want to"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'role']
    
    def signup(self, request, user):
        user.role = self.cleaned_data['role']
        user.save()