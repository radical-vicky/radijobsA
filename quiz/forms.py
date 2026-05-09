from django import forms
from .models import QuizQuestion

class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'time_limit_seconds', 'order_index']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
            'option_a': forms.TextInput(attrs={'class': 'w-full'}),
            'option_b': forms.TextInput(attrs={'class': 'w-full'}),
            'option_c': forms.TextInput(attrs={'class': 'w-full'}),
            'option_d': forms.TextInput(attrs={'class': 'w-full'}),
        }