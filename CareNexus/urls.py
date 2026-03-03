from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views 

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('ai-agent/', views.ai_agent_page, name='ai_agent'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    path('analyze-prescription/', views.analyze_prescription_view, name='analyze_prescription'),

    path('services/', views.service_list_view, name='service_list'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),
    path('others/', views.others_view, name='others'),

    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('my-prescriptions/', views.view_my_prescriptions, name='view_my_prescriptions'),
    path('prescription-ai/<int:pk>/', views.prescription_detail_ai, name='prescription_detail_ai'),

    path('admin-patient-list/', views.admin_patient_list, name='admin_patient_list'),
    path('create-prescription/<int:appt_id>/', views.create_prescription_view, name='create_prescription'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)