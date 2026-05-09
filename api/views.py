from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from jobs.models import Job
from application.models import Application
from tasks.models import Task
from wallet.models import UserWallet, Transaction

User = get_user_model()

@api_view(['GET'])
def api_root(request):
    return Response({
        'message': 'RadiloxRemoteJobs API',
        'version': '1.0',
        'endpoints': {
            'jobs': '/api/jobs/',
            'applications': '/api/applications/',
            'tasks': '/api/tasks/',
            'wallet': '/api/wallet/',
        }
    })

@api_view(['GET'])
def jobs_list(request):
    jobs = Job.objects.filter(is_active=True).values('id', 'title', 'company', 'salary_range', 'location')
    return Response(list(jobs))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_wallet(request):
    wallet, created = UserWallet.objects.get_or_create(user=request.user)
    return Response({
        'balance': wallet.balance,
        'total_earned': wallet.total_earned,
        'total_withdrawn': wallet.total_withdrawn,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_transactions(request):
    transactions = Transaction.objects.filter(user=request.user).values(
        'transaction_type', 'amount', 'net_amount', 'description', 'created_at'
    )[:50]
    return Response(list(transactions))