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
আপনার কাজ হলো রোগীদের তথ্য দিয়ে সাহায্য করা এবং অ্যাডমিনকে ডেটাবেস ম্যানেজ করতে সাহায্য করা।

অ্যাডমিন কমান্ড গাইড:
১. যদি অ্যাডমিন কোনো সার্ভিসের নাম এবং টাকা উল্লেখ করে (যেমন: 'X-Ray ৫০০ টাকা'), আপনি সেটি আপডেট করবেন।
২. যদি কোনো সার্ভিস ডিলিট করতে বলে, আপনি নিশ্চিত করবেন।
৩. উত্তর সবসময় পেশাদার এবং শুদ্ধ বাংলায় দেবেন।"""

# ────────────────────────────────────────────────
# Home & Public Views
# ────────────────────────────────────────────────
def home_view(request):
    """মূল হোম পেজ রেন্ডার করে"""
    return render(request, 'core/home.html')

def service_list_view(request):
    """লগইন ছাড়াই সবাই হাসপাতাল সার্ভিসের তালিকা দেখতে পারবে"""
    services = HospitalService.objects.all().order_by('service_name')
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
        
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        
        messages.success(request, "রেজিস্ট্রেশন সফল হয়েছে! দয়া করে লগইন করুন।")
        return redirect('login')
    return render(request, 'core/register.html')

def login_view(request):
    if request.method == "POST":
        user_type = request.POST.get('user_type')
        if user_type == 'admin':
            admin_pass = request.POST.get('admin_pass')
            if admin_pass == "000":
                user = User.objects.filter(is_superuser=True).first()
                if user:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('ai_agent')
            messages.error(request, "অ্যাডমিন পাসওয়ার্ড সঠিক নয়!")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"স্বাগতম {user.username}!")
                return redirect('home')
            messages.error(request, "ভুল মোবাইল নাম্বার বা ইউজার পাওয়া যায়নি।")
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "সফলভাবে লগআউট করা হয়েছে।")
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

    # ১. অ্যাডমিন মোড: ডাটাবেস আপডেট এবং ডিলিট লজিক
    if request.user.is_superuser:
        
        # ডিলিট লজিক: "ডিলিট করো এক্স-রে" বা "এক্স-রে ডিলিট করো"
        if any(word in user_message for word in ["ডিলিট", "রিমুভ", "বাতিল", "মুছে"]):
            target_service = re.sub(r'ডিলিট|রিমুভ|বাতিল|মুছে|ফেলো|করো|সার্ভিস|লিস্ট|থেকে', '', user_message).strip()
            if target_service:
                # __iexact ব্যবহার করা হয়েছে যাতে ডুপ্লিকেট বা ভুল ডিলিট না হয়
                deleted_count, _ = HospitalService.objects.filter(service_name__icontains=target_service).delete()
                if deleted_count > 0:
                    return JsonResponse({'reply': f"ঠিক আছে অ্যাডমিন, আমি '{target_service}' সংক্রান্ত সকল ডেটাবেস এন্ট্রি মুছে ফেলেছি।"})
                return JsonResponse({'reply': f"দুঃখিত, '{target_service}' নামে কোনো সার্ভিস খুঁজে পাওয়া যায়নি।"})

        # আপডেট বা অ্যাড লজিক (একই নামে ডুপ্লিকেট রোধ)
        price_match = re.search(r'(\d+)', user_message)
        if price_match:
            new_price = price_match.group(1)
            service_name_part = re.sub(r'\d+|টাকা|বিল|খরচ|সেট|করো|আপডেট|মূল্য', '', user_message).strip()
            
            if service_name_part:
                # update_or_create ব্যবহার করা হয়েছে যাতে একই নামের ওপরই কাজ হয়
                obj, created = HospitalService.objects.update_or_create(
                    service_name__iexact=service_name_part,
                    defaults={'price': new_price, 'category': 'SERVICE'}
                )
                status = "নতুন যোগ" if created else "সফলভাবে আপডেট"
                return JsonResponse({'reply': f"অ্যাডমিন, '{service_name_part}' সার্ভিসটি {status} করা হয়েছে। বর্তমান মূল্য: {new_price} ৳।"})

    # ২. ডাটাবেস থেকে তথ্য সংগ্রহ (Context for AI)
    context_data = "বর্তমান সার্ভিসের কিছু নমুনা:\n"
    services_sample = HospitalService.objects.all()[:5]
    context_data += "\n".join([f"- {s.service_name}: {s.price}tk" for s in services_sample])

    # ৩. এপিআই কল (OpenRouter)
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
                    {"role": "user", "content": f"Context: {context_data}\nQuestion: {user_message}"}
                ],
                "temperature": 0.5
            },
            timeout=15
        )
        ai_reply = api_response.json()['choices'][0]['message']['content']
        return JsonResponse({'reply': ai_reply})
    except Exception as e:
        return JsonResponse({'reply': "এআই কানেকশনে সমস্যা হচ্ছে, তবে আপনার কমান্ডটি ডাটাবেসে চেক করুন।"})

# ────────────────────────────────────────────────
# Manual Admin Actions
# ────────────────────────────────────────────────
@user_passes_test(lambda u: u.is_superuser)
def manual_service_edit(request):
    return redirect('/admin/core/hospitalservice/')