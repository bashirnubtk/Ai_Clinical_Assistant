import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test

# মডেল এবং এআই ইঞ্জিন ইম্পোর্ট
from .models import PatientProfile, Doctor, BloodDonor, HospitalService
from .ai_engine import process_ai_command

# ────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & GLOBAL VARIABLES
# ────────────────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "openrouter/free"

SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের একজন অত্যন্ত দক্ষ AI সহকারী। 
আপনার কাজ হলো রোগীদের ধাপে ধাপে সাহায্য করা। রোগী কোনো সমস্যার কথা বললে তাকে দয়া দেখিয়ে সেই বিষয়ের ডাক্তারের নাম সাজেস্ট করুন। 
একবারে সব না বলে কথোপকথন চালিয়ে যান। অ্যাডমিনের জন্য আপনি একজন দক্ষ ডাটাবেস অপারেটর।"""

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 01: AUTHENTICATION VIEWS (LOGIN, REGISTER, LOGOUT)
# ────────────────────────────────────────────────────────────────────────────────

def register_view(request):
    """নতুন রোগীদের নিবন্ধনের জন্য বিস্তারিত ভিউ"""
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        
        if not full_name or not mobile:
            messages.warning(request, "দয়া করে নাম এবং মোবাইল নম্বর দুটিই প্রদান করুন।")
            return redirect('register')

        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই নম্বরটি আগেই নিবন্ধিত হয়েছে।")
            return redirect('register')
        
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        messages.success(request, "রেজিস্ট্রেশন সফল! এখন আপনি লগইন করতে পারবেন।")
        return redirect('login')
    return render(request, 'core/register.html')

def login_view(request):
    """অ্যাডমিন এবং সাধারণ ইউজারদের জন্য পৃথক লগইন গেটওয়ে"""
    if request.method == "POST":
        user_type = request.POST.get('user_type')
        if user_type == 'admin':
            admin_pass = request.POST.get('admin_pass')
            if admin_pass == "000":
                user = User.objects.filter(is_superuser=True).first()
                if user:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, "অ্যাডমিন প্যানেলে স্বাগতম!")
                    return redirect('ai_agent')
            messages.error(request, "অ্যাডমিন পাসওয়ার্ড ভুল।")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"স্বাগতম {user.username}!")
                return redirect('home')
            messages.error(request, "ইউজার পাওয়া যায়নি বা নম্বর ভুল।")
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "সফলভাবে লগআউট করা হয়েছে।")
    return redirect('home')

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 02: CORE PAGES & LIST VIEWS
# ────────────────────────────────────────────────────────────────────────────────

def home_view(request):
    """মূল হোমপেজ রেন্ডার করা"""
    return render(request, 'core/home.html')

def doctor_list_view(request):
    """সকল ডাক্তারের তালিকা প্রদর্শনী"""
    doctors = Doctor.objects.all().order_by('name')
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

def service_list_view(request):
    """সার্ভিস ও বিলিং তালিকা"""
    services = HospitalService.objects.all().order_by('service_name')
    return render(request, 'core/service_list.html', {'services': services})

def blood_bank_view(request):
    """রক্তদাতাদের তালিকা"""
    donors = BloodDonor.objects.all().order_by('blood_group')
    return render(request, 'core/blood_bank.html', {'donors': donors})

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 03: AI AGENT INTERFACE & AJAX LOGIC
# ────────────────────────────────────────────────────────────────────────────────

@login_required
def ai_agent_page(request):
    """এআই চ্যাট ইন্টারফেস পেজ"""
    return render(request, 'core/ai_agent.html')

def ask_ai(request):
    """এই ফাংশনটি এআই ইঞ্জিনের সাথে যোগাযোগ স্থাপন করে"""
    if request.method == "POST":
        user_message = request.POST.get('message', '').strip()
        if not user_message:
            return JsonResponse({'reply': "দয়া করে কিছু টাইপ করুন।"})

        # ai_engine.py থেকে প্রসেসিং লজিক কল করা হচ্ছে
        reply = process_ai_command(
            request.user, 
            user_message, 
            OPENROUTER_API_KEY, 
            MODEL_NAME, 
            SYSTEM_PROMPT
        )
        return JsonResponse({'reply': reply})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 04: MANUAL DB CONTROLS (FOR ADMIN BUTTONS)
# ────────────────────────────────────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_superuser)
def manual_update_redirect(request, model_name):
    """সাইডবার বাটন থেকে সরাসরি ডাটাবেস এডিট করার লিংক"""
    if model_name == 'service':
        return redirect('/admin/core/hospitalservice/')
    elif model_name == 'doctor':
        return redirect('/admin/core/doctor/')
    elif model_name == 'donor':
        return redirect('/admin/core/blooddonor/')
    return redirect('ai_agent')