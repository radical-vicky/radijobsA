from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('cookies/', views.cookies, name='cookies'),
    path('accessibility/', views.accessibility, name='accessibility'),
    
    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    
    # FAQ helpful feedback (AJAX)
    path('faq/<int:faq_id>/helpful/', views.faq_helpful, name='faq_helpful'),
    
    # Admin contact management
    path('admin/contact-messages/', views.admin_contact_messages, name='admin_contact_messages'),
    path('admin/contact-message/<int:pk>/', views.admin_contact_detail, name='admin_contact_detail'),
    path('admin/contact-messages/export/', views.admin_export_contact_messages, name='admin_export_contact_messages'),
    path('admin/faq/manage/', views.admin_faq_manage, name='admin_faq_manage'),
    path('admin/newsletter/subscribers/', views.admin_newsletter_subscribers, name='admin_newsletter_subscribers'),
    
    # AJAX endpoints
    path('ajax/contact/', views.ajax_contact_submit, name='ajax_contact_submit'),
]