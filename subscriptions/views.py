from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import uuid


@login_required
def subscribe(request):
    """Subscription page with payment options"""
    
    if request.user.has_active_subscription:
        messages.warning(request, 'You already have an active subscription.')
        return redirect('subscriptions:status')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'mpesa':
            phone_number = request.POST.get('phone_number', '').strip()
            amount = int(getattr(settings, 'SUBSCRIPTION_PRICE_KES', 2000))
            
            if not phone_number:
                messages.error(request, 'Please enter your M-Pesa phone number')
                return redirect('subscriptions:subscribe')
            
            # Validate phone number
            if not phone_number.startswith('07') and not phone_number.startswith('01') and not phone_number.startswith('254'):
                messages.error(request, 'Please enter a valid Kenyan phone number (e.g., 0712345678)')
                return redirect('subscriptions:subscribe')
            
            # Create transaction in payments
            from payments.models import PaymentTransaction
            
            transaction = PaymentTransaction.objects.create(
                user=request.user,
                payment_type='subscription',
                payment_method='mpesa',
                amount=amount,
                fee=0,
                net_amount=amount,
                currency='KES',
                transaction_id=f"SUB-{uuid.uuid4().hex[:8].upper()}",
                status='pending'
            )
            
            # Store in session for the payment processing
            request.session['transaction_id'] = transaction.id
            request.session['mpesa_phone'] = phone_number
            
            # Redirect to M-Pesa processing
            return redirect('payments:mpesa_process')
        
        elif payment_method == 'paypal':
            messages.info(request, 'PayPal integration coming soon.')
            return redirect('subscriptions:subscribe')
        
        elif payment_method == 'bank':
            messages.info(request, 'Bank transfer details will be sent to your email.')
            return redirect('subscriptions:subscribe')
        
        else:
            messages.error(request, 'Invalid payment method selected.')
            return redirect('subscriptions:subscribe')
    
    context = {
        'price': getattr(settings, 'SUBSCRIPTION_PRICE_USD', 19),
        'price_kes': getattr(settings, 'SUBSCRIPTION_PRICE_KES', 2000),
    }
    return render(request, 'subscriptions/subscribe.html', context)


@login_required
def subscription_status(request):
    """View subscription status"""
    # Check if subscription has expired
    if request.user.has_active_subscription and request.user.subscription_expires_at:
        if request.user.subscription_expires_at < timezone.now():
            request.user.has_active_subscription = False
            request.user.save()
            messages.info(request, 'Your subscription has expired. Please renew to continue.')
    
    return render(request, 'subscriptions/status.html')


@login_required
def cancel_subscription(request):
    """Cancel subscription"""
    if request.method == 'POST':
        if request.user.has_active_subscription:
            request.user.has_active_subscription = False
            request.user.save()
            
            from notifications.models import create_notification
            create_notification(
                user=request.user,
                notification_type='subscription',
                title='Subscription Cancelled',
                message='Your subscription has been cancelled.',
                link='/subscriptions/'
            )
            
            messages.info(request, 'Your subscription has been cancelled.')
        else:
            messages.warning(request, 'No active subscription to cancel.')
        
        return redirect('subscriptions:subscribe')
    
    return render(request, 'subscriptions/cancel.html')