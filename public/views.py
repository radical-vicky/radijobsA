from django.shortcuts import render
from jobs.models import Job

def job_list_public(request):
    jobs = Job.objects.filter(is_active=True)
    return render(request, 'public/jobs.html', {'jobs': jobs})

def job_detail_public(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    return render(request, 'public/job_detail.html', {'job': job})