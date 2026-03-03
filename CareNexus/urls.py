from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views 

urlpatterns = [
    # মূল পেজ ও অথেন্টিকেশন
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # AI এজেন্ট (টেক্সট চ্যাট)
    path('ai-agent/', views.ai_agent_page, name='ai_agent'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    
    # AI Robot (প্রেসক্রিপশন ছবি এনালিসিস)
    path('analyze-prescription/', views.analyze_prescription_view, name='analyze_prescription'),

    # অন্যান্য সার্ভিস
    path('services/', views.service_list_view, name='service_list'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),

    # রোগী কেন্দ্রিক
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('my-prescriptions/', views.view_my_prescriptions, name='view_my_prescriptions'),
    path('prescription-ai/<int:pk>/', views.prescription_detail_ai, name='prescription_detail_ai'),

    # অ্যাডমিন কেন্দ্রিক
    path('admin-patient-list/', views.admin_patient_list, name='admin_patient_list'),
    path('create-prescription/<int:appt_id>/', views.create_prescription_view, name='create_prescription'),
]

# ইমেজ বা মিডিয়া ফাইল সাপোর্ট করার জন্য (ডেভেলপমেন্ট মোডে) এবং ব্র্যাকেট ক্লোজ করা হলো
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)