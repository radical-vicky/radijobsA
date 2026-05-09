from django import forms
from .models import ContactMessage, NewsletterSubscriber

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white transition body-text',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white transition body-text',
                'placeholder': 'you@example.com'
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white transition body-text'
            }),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'class': 'w-full px-4 py-2.5 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white transition body-text',
                'placeholder': 'How can we help you? Please provide as much detail as possible...'
            }),
        }


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email', 'name']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white',
                'placeholder': 'Enter your email'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-github-bg border border-github-border rounded-lg focus:ring-2 focus:ring-github-accent focus:border-github-accent text-white',
                'placeholder': 'Your name (optional)'
            }),
        }