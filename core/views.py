import os
import requests

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from .models import PatientProfile, Doctor, BloodDonor

# ────────────────────────────────────────────────
# OpenRouter API Configuration
# ────────────────────────────────────────────────
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "openrouter/free"  # Free model

SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের স্মার্ট AI সহকারী।
সবসময় সংক্ষিপ্ত, বন্ধুত্বপূর্ণ ও আধুনিক বাংলায় উত্তর দিন।
চ্যাটিং শুরু করার আগে সৌজন্যমূলক কথা যোগ করুন।

নির্দেশনা:
- শুধুমাত্র হাসপাতাল সম্পর্কিত প্রশ্নের উত্তর দিন।
- ডাক্তার, রক্তদাতা, পেশেন্ট তথ্য থাকলে লিস্ট দেখান।
- সাধারণ কথোপকথন হলে ডাটাবেস লিস্ট ছাড়াই সৌজন্যমূলক উত্তর দিন।
- তথ্য না থাকলে বলুন "বর্তমানে এই তথ্য নেই, ফ্রন্ট ডেস্কে যোগাযোগ করুন।"
"""

# ────────────────────────────────────────────────
# Home Page
# ────────────────────────────────────────────────
def home_view(request):
    return render(request, 'core/home.html')

# ────────────────────────────────────────────────
# Register
# ────────────────────────────────────────────────
def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই নাম্বার দিয়ে অলরেডি রেজিস্ট্রেশন করা আছে।")
            return redirect('register')
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        messages.success(request, "রেজিস্ট্রেশন সফল! এখন লগইন করুন।")
        return redirect('login')
    return render(request, 'core/register.html')

# ────────────────────────────────────────────────
# Login
# ────────────────────────────────────────────────
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
            messages.error(request, "ভুল অ্যাডমিন পাসওয়ার্ড!")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"স্বাগতম, {user.username}!")
                return redirect('home')
            messages.error(request, "ভুল মোবাইল নাম্বার বা অ্যাকাউন্ট নেই।")
    return render(request, 'core/login.html')

# ────────────────────────────────────────────────
# Logout
# ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.info(request, "লগআউট সফল হয়েছে।")
    return redirect('home')

# ────────────────────────────────────────────────
# AI Agent Page
# ────────────────────────────────────────────────
def ai_agent_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'core/ai_agent.html')

# ────────────────────────────────────────────────
# Doctor List
# ────────────────────────────────────────────────
def doctor_list_view(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

# ────────────────────────────────────────────────
# Blood Bank
# ────────────────────────────────────────────────
def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})

# ────────────────────────────────────────────────
# Ask AI (Final Working Logic)
# ────────────────────────────────────────────────
def ask_ai(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'reply': "দয়া করে কিছু লিখুন..."})

    user_message_lower = user_message.lower()
    relevant_context = ""

    # ডাক্তার তথ্য
    if any(word in user_message_lower for word in ["ডাক্তার", "doctor", "specialist", "expert"]):
        doctors = Doctor.objects.all()
        doc_info = "\n".join([f"• {d.name} — {d.specialty} ({d.schedule})" for d in doctors])
        relevant_context += f"\n[ডাক্তারদের তালিকা]:\n{doc_info or 'কোনো তথ্য নেই।'}"

    # রক্তদাতা তথ্য
    if any(word in user_message_lower for word in ["রক্ত", "blood", "donor", "দাতা"]):
        donors = BloodDonor.objects.all()
        donor_info = "\n".join([f"• {b.donor_name} — {b.blood_group} ({b.contact})" for b in donors])
        relevant_context += f"\n[রক্তদাতাদের তালিকা]:\n{donor_info or 'কোনো তথ্য নেই।'}"

    # পেশেন্ট তথ্য (অ্যাডমিন)
    if request.user.is_superuser:
        if any(word in user_message_lower for word in ["পেশেন্ট", "patient", "রোগী"]):
            patients = PatientProfile.objects.all()
            patient_info = f"মোট পেশেন্ট: {patients.count()}\n" + "\n".join([f"• {p.full_name} — {p.mobile_number}" for p in patients])
            relevant_context += f"\n[পেশেন্ট তথ্য]:\n{patient_info or 'কোনো তথ্য নেই।'}"

    # ফাইনাল প্রম্পট
    if relevant_context:
        full_prompt = f"হাসপাতালের ডাটাবেস তথ্য:\n{relevant_context}\n\nইউজারের প্রশ্ন: {user_message}\n\nনির্দেশনা: ওপরের তথ্য ব্যবহার করে উত্তর দিন।"
    else:
        full_prompt = f"ইউজারের প্রশ্ন: {user_message}\n\nনির্দেশনা: ইউজার সাধারণ কথা বলেছে। কোনো ডাটাবেস লিস্ট ছাড়াই সৌজন্যমূলক উত্তর দিন।"

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt},
                ],
                "temperature": 0.5,
            },
            timeout=30
        )
        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content'].strip()
        return JsonResponse({'reply': reply})

    except requests.exceptions.RequestException as e:
        print(f"❌ OpenRouter Error: {str(e)}")
        return JsonResponse({'reply': "সার্ভারে সমস্যা হচ্ছে, কিছুক্ষণ পর চেষ্টা করুন।"})
