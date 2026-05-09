from django import forms
from .models import SubscriptionPlan

class SubscriptionPlanForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = ['name', 'price_usd', 'duration_days', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border rounded-lg p-2'}),
            'price_usd': forms.NumberInput(attrs={'class': 'w-full border rounded-lg p-2', 'step': '0.01'}),
            'duration_days': forms.NumberInput(attrs={'class': 'w-full border rounded-lg p-2'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }