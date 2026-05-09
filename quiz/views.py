from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
import json
from .models import QuizResult, QuizQuestion
from application.models import Application
from notifications.models import create_notification


@login_required
def my_quizzes(request):
    """View all quizzes taken by the user"""
    quizzes = QuizResult.objects.filter(application__user=request.user).select_related('application__job').order_by('-completed_at')
    
    context = {
        'quizzes': quizzes,
    }
    return render(request, 'quiz/my_quizzes.html', context)


@login_required
def take_quiz(request, application_id):
    """Take a quiz for a job application with timer"""
    application = get_object_or_404(Application, id=application_id, user=request.user)
    
    # Check if application is approved
    if application.status != 'approved':
        messages.error(request, 'Your application must be approved before taking the quiz.')
        return redirect('application:my_applications')
    
    # Check if quiz already taken
    if QuizResult.objects.filter(application=application).exists():
        messages.warning(request, 'You have already taken the quiz for this job.')
        return redirect('quiz:result', application_id=application.id)
    
    # Check if quiz has expired
    if application.quiz_expires_at and application.quiz_expires_at < timezone.now():
        messages.error(request, f'Your quiz deadline has passed. It expired on {application.quiz_expires_at.strftime("%B %d, %Y")}.')
        return redirect('application:my_applications')
    
    # Get quiz questions
    try:
        from quiz.models import QuizQuestion
        questions = QuizQuestion.objects.filter(job=application.job, is_active=True)
    except:
        # If no quiz questions exist, create sample questions
        questions = []
    
    if not questions:
        messages.error(request, 'No quiz questions available for this job.')
        return redirect('application:my_applications')
    
    # Calculate remaining time
    remaining_seconds = application.quiz_duration_minutes * 60
    quiz_started_at = request.session.get(f'quiz_started_{application.id}')
    
    if quiz_started_at:
        started = timezone.datetime.fromisoformat(quiz_started_at)
        elapsed = (timezone.now() - started).total_seconds()
        remaining_seconds = max(0, remaining_seconds - elapsed)
    
    if request.method == 'POST':
        # Process quiz answers
        score = 0
        total_questions = questions.count()
        
        for question in questions:
            user_answer = request.POST.get(f'question_{question.id}')
            if user_answer and user_answer == question.correct_answer:
                score += 1
        
        final_score = int((score / total_questions) * 100) if total_questions > 0 else 0
        
        # Save quiz result
        quiz_result = QuizResult.objects.create(
            application=application,
            score=final_score,
            passed=final_score >= 70,
            completed_at=timezone.now(),
            max_score=100,
            answers=json.dumps(request.POST.dict())
        )
        
        # Update application
        application.quiz_score = final_score
        application.quiz_taken_at = timezone.now()
        application.save()
        
        # Clear session data
        request.session.pop(f'quiz_started_{application.id}', None)
        
        # Create result notification
        if final_score >= 70:
            create_notification(
                user=request.user,
                notification_type='quiz',
                title='Quiz Passed!',
                message=f'Congratulations! You scored {final_score}% on the {application.job.title} quiz. Your application has been moved to the interview stage.',
                link=f'/quiz/result/{application.id}/'
            )
            messages.success(request, f'Quiz completed! You scored {final_score}%. You passed!')
        else:
            create_notification(
                user=request.user,
                notification_type='quiz',
                title='Quiz Result Available',
                message=f'You scored {final_score}% on the {application.job.title} quiz. The passing score is 70%.',
                link=f'/quiz/result/{application.id}/'
            )
            messages.warning(request, f'Quiz completed! You scored {final_score}%. The passing score is 70%.')
        
        return redirect('quiz:result', application_id=application.id)
    
    # Start quiz session
    if not quiz_started_at:
        request.session[f'quiz_started_{application.id}'] = timezone.now().isoformat()
    
    context = {
        'application': application,
        'questions': questions,
        'remaining_seconds': remaining_seconds,
        'duration_minutes': application.quiz_duration_minutes,
        'expires_at': application.quiz_expires_at,
    }
    return render(request, 'quiz/take_quiz.html', context)


@login_required
def quiz_result(request, application_id):
    """View quiz result"""
    application = get_object_or_404(Application, id=application_id, user=request.user)
    quiz_result = get_object_or_404(QuizResult, application=application)
    
    context = {
        'application': application,
        'quiz_result': quiz_result,
    }
    return render(request, 'quiz/result.html', context)