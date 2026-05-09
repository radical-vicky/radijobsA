from django.contrib import admin
from .models import QuizQuestion, QuizResult


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'question_text_preview', 'question_type', 'is_active', 'order')
    list_filter = ('job', 'question_type', 'is_active')
    search_fields = ('question_text', 'job__title')
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job',)
        }),
        ('Question Details', {
            'fields': ('question_type', 'question_text', 'points', 'order', 'is_active')
        }),
        ('Options (for multiple choice)', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'),
            'classes': ('wide',)
        }),
    )
    
    def question_text_preview(self, obj):
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    question_text_preview.short_description = 'Question'


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant', 'job', 'score', 'passed', 'completed_at')
    list_filter = ('passed', 'completed_at')
    search_fields = ('application__user__email', 'application__job__title')
    readonly_fields = ('answers',)
    
    def applicant(self, obj):
        return obj.application.user.get_full_name() or obj.application.user.username
    applicant.short_description = 'Applicant'
    
    def job(self, obj):
        return obj.application.job.title
    job.short_description = 'Job'