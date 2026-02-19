import os
import requests  # OpenRouter API-এর জন্য

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from .models import PatientProfile, Doctor, BloodDonor

# ────────────────────────────────────────────────
#         OpenRouter Llama Configuration
# ────────────────────────────────────────────────
OPENROUTER_API_KEY = "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"

# Llama মডেল নাম (ফ্রি ভার্সন)
MODEL_NAME = "meta-llama/llama-3-8b-instruct"

# System Instruction — প্রফেশনাল ও বুদ্ধিমান আচরণের জন্য
SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের স্মার্ট AI সহকারী।
সবসময় খুব ভদ্র, সংক্ষিপ্ত, বন্ধুত্বপূর্ণ ও আধুনিক বাংলায় উত্তর দিন।
চ্যাটিং শুরুর প্রথমে সৌজন্যমূলক কথা যোগ করুন।

আপনার কাজ: শুধু হাসপাতাল-সম্পর্কিত প্রশ্নের উত্তর দেওয়া।
- প্রশ্ন যদি ডাক্তার, রক্তদাতা, পেশেন্ট বা স্বাস্থ্য নিয়ে হয় → তবেই কেবল আপনাকে দেওয়া তথ্য থেকে সরাসরি লিস্ট দিন।
- যদি প্রশ্ন সাধারণ (যেমন "হ্যালো", "কেমন আছো") হয় → তবে ডাটাবেসের লিস্ট দেখাবেন না, শুধু সৌজন্যমূলক উত্তর দিন।
- যদি তথ্য খালি থাকে → বলুন "বর্তমানে এই তথ্য নেই, ফ্রন্ট ডেস্কে যোগাযোগ করুন।"
- কোনো কাল্পনিক তথ্য বা বাইরের কোনো ডাক্তার/হাসপাতালের নাম বলবেন না।

ভাষার ব্যবহার:
- শুদ্ধ বাংলা ব্যবহার করুন।
- যদি কোনো প্রযুক্তিগত শব্দ বাংলায় কঠিন হয়, তবে ইংরেজিতে লিখুন।
উত্তরের শেষে সৌজন্যমূলক কথা যোগ করুন।
"""

# ────────────────────────────────────────────────
#         START: home_view
# ────────────────────────────────────────────────
def home_view(request):
    return render(request, 'core/home.html')

# ────────────────────────────────────────────────
#         START: register_view
# ────────────────────────────────────────────────
def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই নাম্বার দিয়ে অলরেডি রেজিস্ট্রেশন করা আছে।")
            return redirect('register')
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        messages.success(request, "রেজিস্ট্রেশন সফল! এখন লগইন করুন।")
        return redirect('login')
    return render(request, 'core/register.html')

# ────────────────────────────────────────────────
#         START: login_view
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
#         START: logout_view
# ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.info(request, "লগআউট সফল হয়েছে।")
    return redirect('home')

# ────────────────────────────────────────────────
#         START: ai_agent_page
# ────────────────────────────────────────────────
def ai_agent_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'core/ai_agent.html')

# ────────────────────────────────────────────────
#         START: doctor_list_view
# ────────────────────────────────────────────────
def doctor_list_view(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

# ────────────────────────────────────────────────
#         START: blood_bank_view
# ────────────────────────────────────────────────
def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})

# ────────────────────────────────────────────────
#         START: ask_ai (Updated Logic)
# ────────────────────────────────────────────────
def ask_ai(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    user_message = request.POST.get('message', '').strip().lower()
    if not user_message:
        return JsonResponse({'reply': "দয়া করে কিছু লিখুন..."})

    # ১. ইন্টেন্ট ফিল্টারিং (AI-কে অপ্রাসঙ্গিক তথ্য দেওয়া বন্ধ করতে)
    relevant_context = ""
    
    # ডাক্তার সম্পর্কিত কিউয়ার্ড চেক
    if any(word in user_message for word in ["ডাক্তার", "doctor", "specialist", "expert"]):
        doctors = Doctor.objects.all()
        doc_info = "\n".join([f"• {d.name} — {d.specialty} ({d.schedule})" for d in doctors])
        relevant_context += f"\n[ডাক্তারদের তালিকা]:\n{doc_info or 'কোনো তথ্য নেই।'}"

    # রক্তদাতা সম্পর্কিত কিউয়ার্ড চেক
    if any(word in user_message for word in ["রক্ত", "blood", "donor", "দাতা"]):
        donors = BloodDonor.objects.all()
        donor_info = "\n".join([f"• {b.donor_name} — {b.blood_group} ({b.contact})" for b in donors])
        relevant_context += f"\n[রক্তদাতাদের তালিকা]:\n{donor_info or 'কোনো তথ্য নেই।'}"

    # অ্যাডমিন হলে পেশেন্ট তথ্য চেক
    if request.user.is_superuser:
        if any(word in user_message for word in ["পেশেন্ট", "patient", "রোগী"]):
            patients = PatientProfile.objects.all()
            patient_info = f"মোট পেশেন্ট: {patients.count()}\n" + "\n".join([f"• {p.full_name} — {p.mobile_number}" for p in patients])
            relevant_context += f"\n[পেশেন্ট তথ্য]:\n{patient_info or 'কোনো তথ্য নেই।'}"

    # ২. ফাইনাল প্রম্পট গঠন
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
                "temperature": 0.5, # উত্তরকে আরো টু-দ্য-পয়েন্ট রাখার জন্য
            }
        )

        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content'].strip()
        return JsonResponse({'reply': reply})

    except requests.exceptions.RequestException as e:
        print(f"❌ OpenRouter Error: {str(e)}")
        return JsonResponse({'reply': "সার্ভারে সমস্যা হচ্ছে, কিছুক্ষণ পর চেষ্টা করুন।"})

# ────────────────────────────────────────────────
#         END: ask_ai
# ────────────────────────────────────────────────

