from django import forms
from .models import Task, TaskComment

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'job', 'assigned_to', 'budget_amount', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border rounded-lg p-2'}),
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full border rounded-lg p-2'}),
            'title': forms.TextInput(attrs={'class': 'w-full border rounded-lg p-2'}),
            'budget_amount': forms.NumberInput(attrs={'class': 'w-full border rounded-lg p-2', 'step': '0.01'}),
            'job': forms.Select(attrs={'class': 'w-full border rounded-lg p-2'}),
            'assigned_to': forms.Select(attrs={'class': 'w-full border rounded-lg p-2'}),
        }

class TaskSubmitForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['submission_url', 'submission_notes']
        widgets = {
            'submission_url': forms.URLInput(attrs={
                'class': 'w-full border rounded-lg p-2',
                'placeholder': 'https://github.com/username/repo or https://your-deployed-app.com'
            }),
            'submission_notes': forms.Textarea(attrs={
                'rows': 5,
                'class': 'w-full border rounded-lg p-2',
                'placeholder': 'Explain what you implemented, any challenges faced, and how to test the submission...'
            }),
        }

class TaskReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('approve', 'Approve Task'),
        ('request_revision', 'Request Revision'),
        ('reject', 'Reject Task'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect)
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full border rounded-lg p-2'}),
        required=False,
        help_text="Provide feedback for revision or rejection"
    )

class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full border rounded-lg p-2',
                'placeholder': 'Write a comment...'
            }),
        }