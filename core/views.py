import os
import requests
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import PatientProfile, Doctor, BloodDonor, HospitalService

# ────────────────────────────────────────────────
# API & System Configuration
# ────────────────────────────────────────────────
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "openrouter/free"

SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের একজন অত্যন্ত দক্ষ AI সহকারী।
আপনার কাজ হলো রোগীদের তথ্য দিয়ে সাহায্য করা এবং অ্যাডমিনকে ডেটাবেস ম্যানেজ করতে সাহায্য করা।

অ্যাডমিন কমান্ড গাইড:
১. যদি অ্যাডমিন কোনো সার্ভিসের নাম এবং টাকা উল্লেখ করে (যেমন: 'X-Ray ৫০০ টাকা'), আপনি সেটি আপডেট করবেন।
২. যদি কোনো সার্ভিস ডিলিট করতে বলে, আপনি নিশ্চিত করবেন।
৩. উত্তর সবসময় পেশাদার এবং শুদ্ধ বাংলায় দেবেন।"""

# ────────────────────────────────────────────────
# Home & Public Views
# ────────────────────────────────────────────────
def home_view(request):
    """মূল হোম পেজ রেন্ডার করে"""
    return render(request, 'core/home.html')

def service_list_view(request):
    """লগইন ছাড়াই সবাই হাসপাতাল সার্ভিসের তালিকা দেখতে পারবে"""
    services = HospitalService.objects.all().order_by('-last_updated')
    return render(request, 'core/service_list.html', {'services': services})

# ────────────────────────────────────────────────
# Authentication (Login, Register, Logout)
# ────────────────────────────────────────────────
def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        
        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই মোবাইল নাম্বারটি ইতিমধ্যে নিবন্ধিত।")
            return redirect('register')
        
        # ইউজার তৈরি (পাসওয়ার্ড হিসেবে মোবাইল নাম্বার সেট করা হচ্ছে লার্নিং পারপাসে)
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        
        messages.success(request, "রেজিস্ট্রেশন সফল হয়েছে! দয়া করে লগইন করুন।")
        return redirect('login')
    return render(request, 'core/register.html')

def login_view(request):
    if request.method == "POST":
        user_type = request.POST.get('user_type')
        if user_type == 'admin':
            admin_pass = request.POST.get('admin_pass')
            # সিম্পল অ্যাডমিন গেটওয়ে
            if admin_pass == "000":
                user = User.objects.filter(is_superuser=True).first()
                if user:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('ai_agent')
            messages.error(request, "অ্যাডমিন পাসওয়ার্ড সঠিক নয়!")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"স্বাগতম {user.username}!")
                return redirect('home')
            messages.error(request, "ভুল মোবাইল নাম্বার বা ইউজার পাওয়া যায়নি।")
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "সফলভাবে লগআউট করা হয়েছে।")
    return redirect('home')

# ────────────────────────────────────────────────
# Core Features (AI Agent, Doctors, Blood Bank)
# ────────────────────────────────────────────────
@login_required
def ai_agent_page(request):
    """এআই চ্যাট ইন্টারফেস যেখানে অ্যাডমিন কমান্ড দিতে পারবে"""
    return render(request, 'core/ai_agent.html')

def doctor_list_view(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})

# ────────────────────────────────────────────────
# The Brain: AI Agent Logic (Ask AI)
# ────────────────────────────────────────────────
def ask_ai(request):
    """এই ফাংশনটি এআই কমান্ড এবং ডাটাবেস অপারেশন হ্যান্ডেল করে"""
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request'}, status=400)

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'reply': "কিছু লিখুন..."})

    user_message_lower = user_message.lower()
    
    # অ্যাডমিন মোড: ম্যানুয়াল কাম এআই ডাটাবেস আপডেট
    if request.user.is_superuser:
        # ১. ডিলিট কমান্ড প্রসেসিং
        if any(word in user_message for word in ["ডিলিট", "রিমুভ", "বাতিল"]):
            # নাম খুঁজে বের করার চেষ্টা
            potential_name = user_message.replace("ডিলিট", "").replace("করো", "").strip()
            deleted_count, _ = HospitalService.objects.filter(service_name__icontains=potential_name).delete()
            if deleted_count > 0:
                return JsonResponse({'reply': f"ঠিক আছে অ্যাডমিন, আমি '{potential_name}' সার্ভিসটি ডাটাবেস থেকে সফলভাবে সরিয়ে দিয়েছি।"})

        # ২. অ্যাড/আপডেট কমান্ড (Regex দিয়ে নাম এবং টাকা আলাদা করা)
        # লজিক: "ডায়ালাইসিস ৫০০ টাকা" -> নাম: ডায়ালাইসিস, মূল্য: ৫০০
        price_match = re.search(r'(\d+)', user_message)
        if price_match:
            new_price = price_match.group(1)
            # টেক্সট থেকে সার্ভিসের নাম বের করা (টাকা এবং কমান্ড শব্দ বাদ দিয়ে)
            service_name_part = re.sub(r'\d+|টাকা|বিল|খরচ|সেট|করো', '', user_message).strip()
            
            if service_name_part:
                obj, created = HospitalService.objects.update_or_create(
                    service_name=service_name_part,
                    defaults={'price': new_price, 'category': 'SERVICE'}
                )
                status = "যোগ" if created else "আপডেট"
                return JsonResponse({'reply': f"সফলভাবে '{service_name_part}' {status} করা হয়েছে। নতুন মূল্য: {new_price} ৳।"})

    # ৩. ডাটাবেস থেকে তথ্য সংগ্রহ (Context for AI)
    context_data = ""
    if "ডাক্তার" in user_message:
        docs = Doctor.objects.all()[:5]
        context_data += "\nডাক্তার তালিকা: " + ", ".join([d.name for d in docs])
    
    if any(word in user_message for word in ["বিল", "সার্ভিস", "খরচ"]):
        services = HospitalService.objects.all()[:5]
        context_data += "\nসার্ভিস মূল্য: " + ", ".join([f"{s.service_name}:{s.price}tk" for s in services])

    # ৪. এপিআই কল (OpenRouter)
    try:
        api_response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Context: {context_data}\nUser: {user_message}"}
                ]
            },
            timeout=15
        )
        ai_reply = api_response.json()['choices'][0]['message']['content']
        return JsonResponse({'reply': ai_reply})
    except Exception as e:
        return JsonResponse({'reply': "দুঃখিত, এআই এখন কানেক্ট হতে পারছে না। তবে আপনার কমান্ডটি প্রসেস করার চেষ্টা করা হচ্ছে।"})

# ────────────────────────────────────────────────
# Manual Admin Actions (আপনার চাহিদা মোতাবেক ম্যানুয়াল লিংক)
# ────────────────────────────────────────────────
@user_passes_test(lambda u: u.is_superuser)
def manual_service_edit(request):
    """অ্যাডমিন সরাসরি ড্যাশবোর্ড থেকে কাজ করতে চাইলে তাকে এখানে পাঠানো হবে"""
    # এটি ডিফল্ট জ্যাঙ্গো অ্যাডমিন প্যানেলে রিডাইরেক্ট করবে
    return redirect('/admin/core/hospitalservice/')