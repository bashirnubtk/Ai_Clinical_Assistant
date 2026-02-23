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
    
    # সার্ভিস, বিলিং, ডাক্তার ও ব্লাড ব্যাংক
    path('services/', views.service_list_view, name='service_list'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),

    # ম্যানুয়াল ডাটাবেস কন্ট্রোল (অ্যাডমিন বাটনগুলোর জন্য)
    # এটি সাইডবারের 'সার্ভিস খরচ আপডেট (Manual)' বাটনকে কাজ করতে সাহায্য করবে
    path('manual-update/<str:model_name>/', views.manual_update_redirect, name='manual_update'),
]