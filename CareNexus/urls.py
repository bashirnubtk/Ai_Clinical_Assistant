from django.contrib import admin
from django.urls import path
from core import views 

urlpatterns = [
    # মূল পেজ ও অথেন্টিকেশন
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # AI এজেন্ট
    path('ai-agent/', views.ai_agent_page, name='ai_agent'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    
    # সার্ভিস ও জেনারেল ভিউ
    path('services/', views.service_list_view, name='service_list'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),

    # রোগী কেন্দ্রিক পাথ (নতুন)
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('my-prescriptions/', views.view_my_prescriptions, name='view_my_prescriptions'),
    path('prescription-ai/<int:pk>/', views.prescription_detail_ai, name='prescription_detail_ai'),

    # অ্যাডমিন কেন্দ্রিক পাথ (নতুন)
    path('admin-patient-list/', views.admin_patient_list, name='admin_patient_list'),
    path('create-prescription/<int:appt_id>/', views.create_prescription_view, name='create_prescription'),

    # ম্যানুয়াল আপডেট
    path('manual-update/<str:model_name>/', views.manual_update_redirect, name='manual_update'),
]