from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('my/', views.my_quizzes, name='my_quizzes'),
    path('take/<int:application_id>/', views.take_quiz, name='take'),
    path('result/<int:application_id>/', views.quiz_result, name='result'),
]