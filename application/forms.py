from django import forms
from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'cover_letter', 
            'repository_link', 
            'deployment_link', 
            'test_credentials', 
            'project_notes', 
            'project_file'
        ]
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-textarea', 
                'rows': 6, 
                'placeholder': 'Tell us about your approach to this project and why you are the right fit...'
            }),
            'repository_link': forms.URLInput(attrs={
                'class': 'form-input', 
                'placeholder': 'https://github.com/username/project'
            }),
            'deployment_link': forms.URLInput(attrs={
                'class': 'form-input', 
                'placeholder': 'https://your-project.vercel.app (optional)'
            }),
            'test_credentials': forms.Textarea(attrs={
                'class': 'form-textarea', 
                'rows': 3, 
                'placeholder': 'Email: test@example.com\nPassword: test123'
            }),
            'project_notes': forms.Textarea(attrs={
                'class': 'form-textarea', 
                'rows': 4, 
                'placeholder': 'Any additional information about your implementation, technologies used, or challenges faced...'
            }),
            'project_file': forms.FileInput(attrs={
                'class': 'form-input file-input', 
                'accept': '.zip,.rar,.pdf'
            }),
        }
        help_texts = {
            'cover_letter': 'Explain your approach to this project and why you are qualified',
            'repository_link': 'Link to your GitHub/GitLab repository containing the project code',
            'deployment_link': 'Optional: Link to live demo of your deployed application',
            'test_credentials': 'Provide test credentials for reviewers to access your deployed site',
            'project_notes': 'Any notes about your implementation, technologies used, or challenges faced',
            'project_file': 'Upload project files as ZIP archive (max 25MB) - optional',
        }