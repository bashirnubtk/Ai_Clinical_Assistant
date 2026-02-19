import requests
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from .models import PatientProfile, Doctor, BloodDonor

OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "meta-llama/llama-3-8b-instruct"

SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের স্মার্ট AI সহকারী। 
সবসময় সংক্ষিপ্ত, বন্ধুত্বপূর্ণ বাংলায় উত্তর দিন। শুধুমাত্র হাসপাতাল সম্পর্কিত প্রশ্নের উত্তর দিন।
"""

def home_view(request):
    return render(request, 'core/home.html')

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

def logout_view(request):
    logout(request)
    messages.info(request, "লগআউট সফল হয়েছে।")
    return redirect('home')

def ai_agent_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'core/ai_agent.html')

def doctor_list_view(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})

def ask_ai(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'reply': "দয়া করে কিছু লিখুন..."})

    doctors = Doctor.objects.all()
    donors = BloodDonor.objects.all()
    patients = PatientProfile.objects.all()

    doc_info = "\n".join([f"• {d.name} — {d.specialty} ({d.schedule})" for d in doctors]) or "কোনো ডাক্তার নেই।"
    donor_info = "\n".join([f"• {b.donor_name} — {b.blood_group} ({b.contact})" for b in donors]) or "কোনো রক্তদাতা নেই।"
    patient_count = patients.count()
    patient_info = f"পেশেন্ট সংখ্যা: {patient_count}\n" + "\n".join([f"• {p.full_name} — {p.mobile_number}" for p in patients]) or "কোনো পেশেন্ট নেই।"

    if request.user.is_superuser:
        full_info = f"ডাক্তারগণ:\n{doc_info}\n\nরক্তদাতাগণ:\n{donor_info}\n\nপেশেন্ট তথ্য:\n{patient_info}"
    else:
        full_info = f"ডাক্তারগণ:\n{doc_info}\n\nরক্তদাতাগণ:\n{donor_info}"

    full_prompt = f"{SYSTEM_PROMPT}\nহাসপাতালের তথ্য:\n{full_info}\n\nপ্রশ্ন: {user_message}"

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL_NAME, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]},
            timeout=30
        )
        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content'].strip()
        return JsonResponse({'reply': reply})

    except requests.exceptions.RequestException as e:
        if "401" in str(e):
            return JsonResponse({'reply': "API কী সঠিক নয়। OpenRouter থেকে চেক করুন।"})
        elif "429" in str(e):
            return JsonResponse({'reply': "রেট লিমিট ছাড়িয়ে গেছে। কিছুক্ষণ পর চেষ্টা করুন।"})
        else:
            return JsonResponse({'reply': "সার্ভারে সমস্যা হচ্ছে, পরে চেষ্টা করুন।"})
