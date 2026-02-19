from django.contrib import admin
from django.urls import path
from core import views 

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ai-agent/', views.ai_agent_page, name='ai_agent'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('blood-bank/', views.blood_bank_view, name='blood_bank'),
]