import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage

# মডেল এবং এআই ইঞ্জিন ইম্পোর্ট
from .models import PatientProfile, Doctor, BloodDonor, HospitalService, Appointment, Prescription
from .ai_engine import process_ai_command
from .ai_prescription_analyzer import extract_text_and_analyze

# CONFIGURATION
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "openrouter/free"
SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের একজন অত্যন্ত দক্ষ এবং দয়ালু AI সহকারী। 
ইউজারদের সাথে মানুষের মতো আন্তরিকভাবে বাংলায় কথা বলুন। 
ডাটাবেস থেকে তথ্য দেওয়া হলে সেই তথ্য নির্ভুলভাবে জানাবেন। 
কোনো তথ্য না থাকলে সরাসরি না বলে সৌজন্যের সাথে ফ্রন্ট ডেস্কে যোগাযোগ করতে বলুন।"""

# --- AUTHENTICATION ---
def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        if not full_name or not mobile:
            messages.warning(request, "নাম এবং মোবাইল নম্বর দিন।")
            return redirect('register')
        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই নম্বরটি অলরেডি নিবন্ধিত।")
            return redirect('register')
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        messages.success(request, "রেজিস্ট্রেশন সফল হয়েছে!")
        return redirect('login')
    return render(request, 'core/register.html')

def login_view(request):
    if request.method == "POST":
        user_type = request.POST.get('user_type')
        if user_type == 'admin':
            if request.POST.get('admin_pass') == "000":
                user = User.objects.filter(is_superuser=True).first()
                if user:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('admin_patient_list')
            messages.error(request, "ভুল অ্যাডমিন পাসওয়ার্ড!")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('home')
            messages.error(request, "অ্যাকাউন্ট নেই বা তথ্য ভুল।")
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

# --- PATIENT INTERFACE ---
def home_view(request):
    return render(request, 'core/home.html')

@login_required
def doctor_list_view(request):
    doctors = Doctor.objects.all().order_by('name')
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

@login_required
def blood_bank_view(request):
    donors = BloodDonor.objects.all()
    return render(request, 'core/blood_bank.html', {'donors': donors})

@login_required
def analyze_prescription_view(request):
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []

    if request.method == 'POST':
        user_msg = request.POST.get('patient_history', '')
        img = request.FILES.get('prescription_image')
        file_full_path = None
        
        if img:
            file_name = default_storage.save(f"temp_uploads/{img.name}", img)
            file_full_path = default_storage.path(file_name)

        ai_reply = extract_text_and_analyze(file_full_path, user_msg, request.user)
        
        # সেভ হিস্ট্রি (সেশন)
        history = request.session['chat_history']
        history.append({'user': user_msg, 'ai': ai_reply})
        request.session['chat_history'] = history[-5:] # শেষ ৫টি মনে রাখবে
        request.session.modified = True

        if file_full_path and os.path.exists(file_full_path):
            os.remove(file_full_path)

        return render(request, 'core/chat_result.html', {'reply': ai_reply, 'user_message': user_msg})
    
    return render(request, 'core/prescription_upload.html')

@login_required
def ask_ai(request):
    """টেক্সট চ্যাটের জন্য প্রধান এপিআই এন্ডপয়েন্ট"""
    if request.method == "POST":
        user_message = request.POST.get('message', '')
        # ai_engine কে কল করা হচ্ছে ডাটাবেস এক্সেসসহ
        reply = process_ai_command(
            request.user, 
            user_message, 
            OPENROUTER_API_KEY, 
            MODEL_NAME, 
            SYSTEM_PROMPT
        )
        return JsonResponse({'reply': reply})
    return JsonResponse({'error': 'Invalid request'}, status=400)

# --- ADMIN INTERFACE ---
@user_passes_test(lambda u: u.is_superuser)
def admin_patient_list(request):
    appointments = Appointment.objects.all().order_by('-created_at')
    return render(request, 'core/admin_patient_list.html', {'appointments': appointments})

@user_passes_test(lambda u: u.is_superuser)
def create_prescription_view(request, appt_id):
    appointment = get_object_or_404(Appointment, id=appt_id)
    if request.method == "POST":
        Prescription.objects.create(
            appointment=appointment, 
            patient=appointment.patient, 
            medicines=request.POST.get('medicines'), 
            advice=request.POST.get('advice')
        )
        appointment.status = 'Approved'
        appointment.save()
        return redirect('admin_patient_list')
    return render(request, 'core/create_prescription.html', {'appointment': appointment})

@login_required
def ai_agent_page(request):
    return render(request, 'core/ai_agent.html')