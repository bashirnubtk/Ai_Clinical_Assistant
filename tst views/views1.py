import os
import requests  # OpenRouter API-এর জন্য

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from .models import PatientProfile, Doctor, BloodDonor

# ────────────────────────────────────────────────
#        OpenRouter Llama Configuration
# ────────────────────────────────────────────────
OPENROUTER_API_KEY = "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"  # তোমার OpenRouter API কী — ঠিক আছে

# Llama মডেল নাম (ফ্রি ভার্সন)
MODEL_NAME = "meta-llama/llama-3-8b-instruct"  # OpenRouter-এ ফ্রি Llama 3.1 — ঠিক আছে

# System Instruction (হাসপাতালের তথ্যের জন্য) — স্পষ্ট, বন্ধুত্বপূর্ণ ও সৌজন্যমূলক
SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের স্মার্ট AI সহকারী।
সবসময় খুব ভদ্র, সংক্ষিপ্ত, বন্ধুত্বপূর্ণ ও আধুনিক বাংলায় উত্তর দিন।
চ্যাটিং শুরুর প্রথমে সৌজন্যমূলক কথা যোগ করুন, যেমন:
- "হ্যালো! আপনার জন্য কী করতে পারি?"
- "খুব ভালো লাগলো আপনার প্রশ্নটা! এখানে তথ্য দিচ্ছি..."
- "অবশ্যই! আপনার জন্য সাজিয়ে দিচ্ছি..."

আপনার কাজ: শুধু হাসপাতাল-সম্পর্কিত প্রশ্নের উত্তর দেওয়া।
- প্রশ্ন যদি ডাক্তার, রক্তদাতা, পেশেন্ট বা স্বাস্থ্য নিয়ে হয় → দেওয়া তথ্য থেকে সরাসরি লিস্ট/সংখ্যা দিন।
- উত্তর সংক্ষিপ্ত ও সুন্দর রাখুন — বুলেট পয়েন্ট বা নম্বর ব্যবহার করুন।
- যদি প্রশ্ন হাসপাতাল-সম্পর্কিত না হয় (যেমন "হ্যালো", "কেমন আছো", "ওকে", "থ্যাঙ্কস", বা অন্য কোনো কথা) → ভদ্রভাবে হাসপাতালের তথ্যে ফিরিয়ে আনুন। উদাহরণ:
  - "হ্যালো! আমি ভালো আছি। হাসপাতালের ডাক্তার বা রক্তদাতা সম্পর্কে কিছু জানতে চান?"
  - "অসংখ্য ধন্যবাদ! আপনার সুস্থতা কামনা করছি। ডাক্তার বা রক্তদাতা সম্পর্কে কোনো প্রশ্ন আছে?"
- যদি তথ্য খালি থাকে → তখনই শুধু বলুন "বর্তমানে এই তথ্য নেই, ফ্রন্ট ডেস্কে যোগাযোগ করুন।"
- কোনো অতিরিক্ত, বিভ্রান্তিকর বা অপ্রাসঙ্গিক কথা যোগ করবেন না।
উত্তরের শেষে সৌজন্যমূলক কথা যোগ করুন, যেমন:
- "আর কোনো সাহায্য লাগলে বলুন!"
- "আপনার সুস্থতা কামনা করছি!"
- "আমি জানি তোমার এই মডেলটি হচ্ছে বাংলা খুব সুন্দর ভাবে বলতে পারেনা তো যতটুক বাংলাদেশি বাংলা ভাষায় কথা বলতে পারেন ততটুকু বলবেন আর যেটুকু ভাষা বাংলাদেশী বাংলা শুদ্ধ ভাষায় আসবে না সেটুক আপনি ইংরেজিতে দেবেন।
"
"""

# ────────────────────────────────────────────────
#        START: home_view
# ────────────────────────────────────────────────
def home_view(request):
    return render(request, 'core/home.html')
# ────────────────────────────────────────────────
#        END: home_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: register_view
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
#        END: register_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: login_view
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
#        END: login_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: logout_view
# ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.info(request, "লগআউট সফল হয়েছে।")
    return redirect('home')
# ────────────────────────────────────────────────
#        END: logout_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: ai_agent_page
# ────────────────────────────────────────────────
def ai_agent_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'core/ai_agent.html')
# ────────────────────────────────────────────────
#        END: ai_agent_page
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: doctor_list_view
# ────────────────────────────────────────────────
def doctor_list_view(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/doctor_list.html', {'doctors': doctors})
# ────────────────────────────────────────────────
#        END: doctor_list_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: blood_bank_view
# ────────────────────────────────────────────────
def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})
# ────────────────────────────────────────────────
#        END: blood_bank_view
# ────────────────────────────────────────────────

# ────────────────────────────────────────────────
#        START: ask_ai
# ────────────────────────────────────────────────
def ask_ai(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'reply': "দয়া করে কিছু লিখুন..."})

    # ডাটাবেস থেকে তথ্য
    doctors = Doctor.objects.all()
    donors = BloodDonor.objects.all()
    patients = PatientProfile.objects.all()

    doc_info = "\n".join([f"• {d.name} — {d.specialty} ({d.schedule})" for d in doctors]) or "কোনো ডাক্তার নেই।"
    donor_info = "\n".join([f"• {b.donor_name} — {b.blood_group} ({b.contact})" for b in donors]) or "কোনো রক্তদাতা নেই।"
    patient_count = patients.count()
    patient_info = f"পেশেন্ট সংখ্যা: {patient_count}\n" + "\n".join([f"• {p.full_name} — {p.mobile_number}" for p in patients]) or "কোনো পেশেন্ট নেই।"

    # রোল চেক — অ্যাডমিন বা পেশেন্ট
    if request.user.is_superuser:  # অ্যাডমিন হলে সব তথ্য দাও
        full_info = f"""
ডাক্তারগণ:
{doc_info}

রক্তদাতাগণ:
{donor_info}

পেশেন্ট তথ্য:
{patient_info}
"""
    else:  # পেশেন্ট হলে শুধু ডাক্তার/রক্তদাতা দাও
        full_info = f"""
ডাক্তারগণ:
{doc_info}

রক্তদাতাগণ:
{donor_info}
"""

    full_prompt = f"""
{SYSTEM_PROMPT}

হাসপাতালের তথ্য:
{full_info}

প্রশ্ন: {user_message}

উত্তর সংক্ষিপ্ত ও সুন্দর রাখুন। যদি প্রশ্ন সরাসরি ডাক্তার/রক্তদাতা/পেশেন্ট নিয়ে হয় → তথ্য দিন। অন্যথায় লিস্ট দেখাবেন না, শুধু সৌজন্যমূলক উত্তর ।
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt},
                ],
            }
        )

        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content'].strip()
        print("✅ AI Response:", reply[:400])  # ডিবাগ
        return JsonResponse({'reply': reply})

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"❌ OpenRouter Error: {error_msg}")
        if "401" in error_msg:
            return JsonResponse({'reply': "API কী সঠিক নয়। OpenRouter থেকে চেক করুন।"})
        elif "429" in error_msg:
            return JsonResponse({'reply': "রেট লিমিট ছাড়িয়ে গেছে। কিছুক্ষণ পর চেষ্টা করুন।"})
        else:
            return JsonResponse({'reply': f"সমস্যা: {error_msg[:150]}..."})
# ────────────────────────────────────────────────
#        END: ask_ai
# ────────────────────────────────────────────────


একটা জিনিস দেখো আমার উপরে কোড কি সুন্দর কমেন্ট করে ডিজাইন করে করে এভাবে কমেন্ট করে দিতে পারবে কোডের ভিতরে আর সম্পূর্ণ কোডটা কোন অংশ আপডেট করতে বলেছে আপডেট করে সম্পূর্ণ কোড দিতে পারবে !

মানে কোডের এ টু জেড অক্ষুন্ন রেখে কিছু চেঞ্জিং না করে যতটুকু অংশ আপডেট করতে চাও ঐটুকু আপডেট করে দিতে পারবে মানে আমার চাহিদা অনুযায়ী