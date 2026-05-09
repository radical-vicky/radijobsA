from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from .models import (
    ContactMessage, ContactInfo, SocialLink, 
    FAQ, NewsletterSubscriber, SiteSettings
)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        'name_email', 
        'subject_badge', 
        'status_badge', 
        'created_at', 
        'response_time_display',
        'action_buttons'
    )
    
    list_filter = ('status', 'subject', 'created_at')
    search_fields = ('name', 'email', 'message', 'admin_notes')
    readonly_fields = ('created_at', 'updated_at', 'ip_address', 'user_agent', 'referred_from')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Status & Response', {
            'fields': ('status', 'admin_notes', 'response_message', 'responded_by', 'replied_at', 'resolved_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'referred_from', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_replied', 'mark_as_resolved', 'mark_as_spam']
    
    def name_email(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            obj.name,
            obj.email
        )
    name_email.short_description = 'Name & Email'
    name_email.admin_order_field = 'name'
    
    def subject_badge(self, obj):
        colors = {
            'general': '#6e7681',
            'hiring': '#2ea043',
            'freelancer': '#58a6ff',
            'payment': '#f0883e',
            'technical': '#da3633',
            'partnership': '#a371f7',
            'bug': '#da3633',
            'feature': '#f0883e',
            'complaint': '#da3633',
        }
        color = colors.get(obj.subject, '#6e7681')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_subject_display()
        )
    subject_badge.short_description = 'Subject'
    
    def status_badge(self, obj):
        status_colors = {
            'new': '#da3633',
            'read': '#f0883e',
            'replied': '#2ea043',
            'archived': '#6e7681',
            'spam': '#6e7681',
        }
        color = status_colors.get(obj.status, '#6e7681')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def response_time_display(self, obj):
        if obj.response_time_hours:
            hours = obj.response_time_hours
            if hours < 1:
                minutes = int(hours * 60)
                return format_html('<span style="color: #2ea043;">{} minutes</span>', minutes)
            elif hours < 24:
                return format_html('<span style="color: #2ea043;">{:.0f} hours</span>', hours)
            else:
                return format_html('<span style="color: #f0883e;">{:.0f} days</span>', hours / 24)
        return '-'
    response_time_display.short_description = 'Response Time'
    
    def action_buttons(self, obj):
        view_url = reverse('home:admin_contact_detail', args=[obj.id])
        return format_html(
            '<a href="{}" style="background-color: #2ea043; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none;">View & Reply</a>',
            view_url
        )
    action_buttons.short_description = 'Actions'
    
    def mark_as_read(self, request, queryset):
        for obj in queryset:
            obj.mark_as_read()
        self.message_user(request, f"{queryset.count()} message(s) marked as read.")
    mark_as_read.short_description = "Mark selected messages as read"
    
    def mark_as_replied(self, request, queryset):
        for obj in queryset:
            obj.mark_as_replied()
        self.message_user(request, f"{queryset.count()} message(s) marked as replied.")
    mark_as_replied.short_description = "Mark selected messages as replied"
    
    def mark_as_resolved(self, request, queryset):
        for obj in queryset:
            obj.mark_as_resolved()
        self.message_user(request, f"{queryset.count()} message(s) archived.")
    mark_as_resolved.short_description = "Archive selected messages"
    
    def mark_as_spam(self, request, queryset):
        for obj in queryset:
            obj.mark_as_spam()
        self.message_user(request, f"{queryset.count()} message(s) marked as spam.")
    mark_as_spam.short_description = "Mark as spam"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('responded_by')


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Email Settings', {
            'fields': ('support_email', 'sales_email', 'careers_email', 'legal_email', 'privacy_email', 'email_response_time')
        }),
        ('Phone Settings', {
            'fields': ('phone_number', 'phone_hours', 'phone_emergency')
        }),
        ('Live Chat Settings', {
            'fields': ('chat_enabled', 'chat_message', 'chat_instruction', 'chat_widget_code')
        }),
        ('Office Hours', {
            'fields': ('monday_friday_hours', 'saturday_hours', 'sunday_hours')
        }),
        ('Address & Map', {
            'fields': ('address', 'map_embed_url', 'latitude', 'longitude'),
            'classes': ('wide',)
        }),
        ('FAQ Section', {
            'fields': ('faq_section_title', 'faq_section_subtitle', 'faq_button_text')
        }),
        ('Newsletter Section', {
            'fields': ('newsletter_enabled', 'newsletter_title', 'newsletter_subtitle', 'newsletter_button_text'),
            'classes': ('collapse',)
        }),
        ('Social Media', {
            'fields': ('twitter_handle', 'linkedin_url', 'github_url', 'facebook_url', 'instagram_url', 'youtube_url', 'tiktok_url', 'discord_url'),
            'classes': ('collapse',)
        }),
        ('Trust Badges', {
            'fields': ('trust_badges',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return not ContactInfo.objects.exists()


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ('platform_icon', 'url', 'order', 'show_in_footer', 'show_in_contact', 'is_active')
    list_filter = ('platform', 'is_active', 'show_in_footer', 'show_in_contact')
    search_fields = ('url',)
    list_editable = ('order', 'show_in_footer', 'show_in_contact', 'is_active')
    
    def platform_icon(self, obj):
        icons = {
            'twitter': '🐦',
            'linkedin': '🔗',
            'github': '🐙',
            'facebook': '📘',
            'instagram': '📷',
            'youtube': '📺',
            'tiktok': '🎵',
            'discord': '🎮',
        }
        icon = icons.get(obj.platform, '🔗')
        return format_html('{} {}', icon, obj.get_platform_display())
    platform_icon.short_description = 'Platform'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'category_badge', 'order', 'helpful_ratio', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('Question & Answer', {
            'fields': ('question', 'answer', 'category')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Analytics', {
            'fields': ('views', 'helpful_count', 'not_helpful_count', 'helpful_percentage'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('views', 'helpful_count', 'not_helpful_count', 'helpful_percentage')
    
    def question_preview(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_preview.short_description = 'Question'
    
    def category_badge(self, obj):
        return format_html('<span style="background-color: #58a6ff; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>', obj.get_category_display())
    category_badge.short_description = 'Category'
    
    def helpful_ratio(self, obj):
        ratio = obj.helpful_percentage
        if ratio >= 80:
            color = '#2ea043'
        elif ratio >= 50:
            color = '#f0883e'
        else:
            color = '#da3633'
        return format_html(
            '<span style="color: {};">{:.0f}% helpful ({} 👍 / {} 👎)</span>',
            color,
            ratio,
            obj.helpful_count,
            obj.not_helpful_count
        )
    helpful_ratio.short_description = 'Helpfulness'


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email', 'name')
    readonly_fields = ('subscribed_at', 'ip_address')
    actions = ['unsubscribe_selected']
    
    def unsubscribe_selected(self, request, queryset):
        for subscriber in queryset:
            subscriber.unsubscribe()
        self.message_user(request, f"{queryset.count()} subscriber(s) unsubscribed.")
    unsubscribe_selected.short_description = "Unsubscribe selected users"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Branding', {
            'fields': ('site_name', 'site_tagline', 'site_logo', 'site_favicon')
        }),
        ('SEO Settings', {
            'fields': ('meta_description', 'meta_keywords', 'google_analytics_id', 'twitter_card_image', 'facebook_og_image')
        }),
        ('Contact Settings', {
            'fields': ('contact_email', 'admin_email')
        }),
        ('Maintenance Mode', {
            'fields': ('maintenance_mode', 'maintenance_message')
        }),
    )
    
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)