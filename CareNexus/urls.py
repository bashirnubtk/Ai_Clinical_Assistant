from django.contrib import admin
from django.urls import path
from core import views 

urlpatterns = [
    # মূল পেজগুলো
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    
    # ইউজার একাউন্ট
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # AI এজেন্ট ও চ্যাট
    path('ai-agent/', views.ai_agent_page, name='ai_agent'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    
    # নতুন সার্ভিস ও বিলিং পেজ (এই লাইনটি এরর সমাধান করবে)
    path('services/', views.service_list_view, name='service_list'),
    
    # ডাক্তার ও ব্লাড ব্যাংক
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),
]