from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import timedelta
from .models import Subscription, SubscriptionPayment


@login_required
def subscribe(request):
    """Subscribe to Pro plan"""
    # Check if user already has active subscription
    try:
        subscription = Subscription.objects.get(user=request.user)
        if subscription.is_active and not subscription.is_expired:
            messages.warning(request, "You already have an active subscription.")
            return redirect('subscriptions:status')
    except Subscription.DoesNotExist:
        pass
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = 19
        
        if payment_method == 'mpesa':
            phone_number = request.POST.get('phone_number')
            
            # Create payment record with pending status
            payment = SubscriptionPayment.objects.create(
                user=request.user,
                payment_method='mpesa',
                amount=amount,
                transaction_id=f"MPESA-{request.user.id}-{int(timezone.now().timestamp())}",
                status='pending'
            )
            
            try:
                from payments.mpesa import MpesaClient
                from django.conf import settings
                
                mpesa = MpesaClient(
                    consumer_key=settings.MPESA_CONSUMER_KEY,
                    consumer_secret=settings.MPESA_CONSUMER_SECRET,
                    passkey=settings.MPESA_PASSKEY,
                    shortcode=settings.MPESA_SHORTCODE
                )
                
                # Initiate STK push
                response = mpesa.stk_push(
                    phone_number=phone_number,
                    amount=amount,
                    account_reference=f"SUB-{request.user.id}",
                    transaction_desc="Subscription Payment"
                )
                
                if response.get('success'):
                    payment.transaction_id = response.get('CheckoutRequestID')
                    payment.save()
                    messages.success(request, "STK push sent to your phone. Please complete the payment on your M-Pesa.")
                    return redirect('subscriptions:status')
                else:
                    payment.status = 'failed'
                    payment.save()
                    messages.error(request, f"Payment initiation failed: {response.get('error')}")
                    return redirect('subscriptions:subscribe')
                    
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Payment error: {str(e)}")
                return redirect('subscriptions:subscribe')
        
        # Other payment methods...
        elif payment_method == 'paypal':
            SubscriptionPayment.objects.create(
                user=request.user,
                payment_method='paypal',
                amount=amount,
                transaction_id=f"PAYPAL-{request.user.id}-{int(timezone.now().timestamp())}",
                status='pending'
            )
            messages.info(request, "PayPal integration coming soon. Please use M-Pesa or Bank Transfer.")
            return redirect('subscriptions:status')
        
        elif payment_method == 'bank':
            transaction_ref = request.POST.get('transaction_ref', '')
            SubscriptionPayment.objects.create(
                user=request.user,
                payment_method='bank',
                amount=amount,
                transaction_id=transaction_ref or f"BANK-{request.user.id}-{int(timezone.now().timestamp())}",
                status='pending_verification'
            )
            messages.success(request, "Your payment is pending verification. We will activate your subscription once confirmed.")
            return redirect('subscriptions:status')
        
        elif payment_method == 'crypto':
            crypto_currency = request.POST.get('crypto_currency', 'USDT')
            SubscriptionPayment.objects.create(
                user=request.user,
                payment_method='crypto',
                amount=amount,
                crypto_currency=crypto_currency,
                transaction_id=f"CRYPTO-{request.user.id}-{int(timezone.now().timestamp())}",
                status='pending_verification',
                metadata={'currency': crypto_currency}
            )
            messages.success(request, f"Please send {crypto_currency} to the wallet address provided.")
            return redirect('subscriptions:status')
    
    return render(request, 'subscriptions/subscribe.html')


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """M-Pesa STK push callback - Automatically activates subscription on success"""
    import json
    
    try:
        data = json.loads(request.body)
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        print(f"[M-Pesa Callback] ID: {checkout_request_id}, Code: {result_code}, Desc: {result_desc}")
        
        # Find the payment record
        try:
            payment = SubscriptionPayment.objects.get(transaction_id=checkout_request_id)
            print(f"[M-Pesa Callback] Found payment {payment.id} for user {payment.user.email}")
            
            if result_code == 0:  # Success
                # Update payment status
                payment.status = 'completed'
                payment.paid_at = timezone.now()
                payment.save()
                print(f"[M-Pesa Callback] ✅ Payment {payment.id} marked as completed")
                
                # Create or update subscription
                subscription, created = Subscription.objects.update_or_create(
                    user=payment.user,
                    defaults={
                        'plan': 'pro',
                        'is_active': True,
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=30),
                    }
                )
                print(f"[M-Pesa Callback] {'Created' if created else 'Updated'} subscription for {payment.user.email}")
                
                # Update user model
                payment.user.has_active_subscription = True
                payment.user.subscription_expires_at = timezone.now() + timedelta(days=30)
                payment.user.save()
                print(f"[M-Pesa Callback] ✅ Subscription activated for {payment.user.email} until {payment.user.subscription_expires_at}")
                
                # Send success notification (optional)
                try:
                    from notifications.utils import create_notification
                    create_notification(
                        user=payment.user,
                        notification_type='payment',
                        title='Payment Successful',
                        message=f'Your subscription payment of ${payment.amount} was successful. Your Pro plan is now active.',
                        link='/subscriptions/status/'
                    )
                except:
                    pass
                
            elif result_code == 1037:  # User cancelled
                payment.status = 'failed'
                payment.save()
                print(f"[M-Pesa Callback] ❌ User cancelled payment: {result_desc}")
                
            elif result_code == 1032:  # Insufficient funds
                payment.status = 'failed'
                payment.save()
                print(f"[M-Pesa Callback] ❌ Insufficient funds: {result_desc}")
                
                # Send notification about insufficient funds
                try:
                    from notifications.utils import create_notification
                    create_notification(
                        user=payment.user,
                        notification_type='payment',
                        title='Payment Failed - Insufficient Funds',
                        message=f'Your payment of ${payment.amount} failed due to insufficient funds. Please try again.',
                        link='/subscriptions/subscribe/'
                    )
                except:
                    pass
                
            else:  # Other errors
                payment.status = 'failed'
                payment.save()
                print(f"[M-Pesa Callback] ❌ Payment failed: {result_desc}")
                
        except SubscriptionPayment.DoesNotExist:
            print(f"[M-Pesa Callback] ⚠️ Payment not found for ID: {checkout_request_id}")
        
    except Exception as e:
        print(f"[M-Pesa Callback] ❌ Error: {e}")
    
    # Always return success to M-Pesa
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})


@login_required
def subscription_status(request):
    """View subscription status and history"""
    try:
        subscription = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        subscription = None
    
    # Calculate subscription status flags FIRST
    has_active_subscription = subscription and subscription.is_active and not subscription.is_expired
    subscription_cancelled = subscription and not subscription.is_active
    subscription_expired = subscription and subscription.is_expired if subscription else False
    
    # Double-check: If user has completed payment but subscription not active
    if not has_active_subscription:
        completed_payment = SubscriptionPayment.objects.filter(
            user=request.user, 
            status='completed'
        ).first()
        
        if completed_payment:
            # Activate subscription automatically
            subscription, created = Subscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'plan': 'pro',
                    'is_active': True,
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=30),
                }
            )
            request.user.has_active_subscription = True
            request.user.subscription_expires_at = timezone.now() + timedelta(days=30)
            request.user.save()
            print(f"[Status Page] Auto-activated subscription for {request.user.email}")
            
            # Recalculate flags
            has_active_subscription = True
            subscription_cancelled = False
            subscription_expired = False
    
    payments = SubscriptionPayment.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate statistics
    total_spent = payments.filter(status='completed').aggregate(total=models.Sum('amount'))['total'] or 0
    payments_count = payments.filter(status='completed').count()
    active_subscription_count = 1 if has_active_subscription else 0
    
    context = {
        'has_active_subscription': has_active_subscription,
        'subscription_cancelled': subscription_cancelled,
        'subscription_expired': subscription_expired,
        'subscription': subscription,
        'payments': payments[:20],
        'total_spent': total_spent,
        'payments_count': payments_count,
        'active_subscription_count': active_subscription_count,
        'subscription_start_date': subscription.start_date if subscription else None,
        'subscription_expires_at': subscription.end_date if subscription else None,
        'days_remaining': subscription.days_remaining if subscription else 0,
    }
    return render(request, 'subscriptions/status.html', context)

@login_required
def cancel_subscription(request):
    """Cancel user's subscription"""
    try:
        subscription = Subscription.objects.get(user=request.user)
        subscription.is_active = False
        subscription.save()
        
        request.user.has_active_subscription = False
        request.user.save()
        
        messages.success(request, "Your subscription has been cancelled.")
    except Subscription.DoesNotExist:
        messages.error(request, "No active subscription found.")
    
    return redirect('subscriptions:status')


@login_required
def process_payment(request):
    """Process payment after method selection"""
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        return redirect('subscriptions:subscribe')
    return redirect('subscriptions:subscribe')