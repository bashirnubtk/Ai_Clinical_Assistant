import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test

# মডেল এবং এআই ইঞ্জিন ইম্পোর্ট
from .models import PatientProfile, Doctor, BloodDonor, HospitalService, Appointment, Prescription, PatientRecord
from .ai_engine import process_ai_command
from .ai_prescription_analyzer import extract_text_and_analyze

# ────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & GLOBAL VARIABLES
# ────────────────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
MODEL_NAME = "openrouter/free"

SYSTEM_PROMPT = """আপনি CareNexus হাসপাতালের একজন অত্যন্ত দক্ষ AI সহকারী। 
আপনার কাজ হলো রোগীদের ধাপে ধাপে সাহায্য করা। রোগী কোনো সমস্যার কথা বললে তাকে দয়া দেখিয়ে সেই বিষয়ের ডাক্তারের নাম সাজেস্ট করুন। 
একবারে সব না বলে কথোপকথন চালিয়ে যান। অ্যাডমিনের জন্য আপনি একজন দক্ষ ডাটাবেস অপারেটর।"""

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 01: AUTHENTICATION VIEWS (LOGIN, REGISTER, LOGOUT)
# ────────────────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile', '').strip()
        
        if not full_name or not mobile:
            messages.warning(request, "দয়া করে নাম এবং মোবাইল নম্বর দুটিই প্রদান করুন।")
            return redirect('register')

        if User.objects.filter(username=mobile).exists():
            messages.error(request, "এই নম্বরটি আগেই নিবন্ধিত হয়েছে।")
            return redirect('register')
        
        user = User.objects.create_user(username=mobile, password=mobile)
        PatientProfile.objects.create(user=user, full_name=full_name, mobile_number=mobile)
        messages.success(request, "রেজিস্ট্রেশন সফল! এখন আপনি লগইন করতে পারবেন।")
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
                    messages.success(request, "অ্যাডমিন প্যানেলে স্বাগতম!")
                    return redirect('admin_patient_list')
            messages.error(request, "অ্যাডমিন পাসওয়ার্ড ভুল।")
        else:
            mobile = request.POST.get('mobile', '').strip()
            user = User.objects.filter(username=mobile).first()
            if user and not user.is_superuser:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"স্বাগতম {user.username}!")
                return redirect('home')
            messages.error(request, "ইউজার পাওয়া যায়নি বা নম্বর ভুল।")
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "সফলভাবে লগআউট করা হয়েছে।")
    return redirect('home')

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 02: PATIENT INTERFACE (DOCTORS, BOOKING, PRESCRIPTIONS)
# ────────────────────────────────────────────────────────────────────────────────

def home_view(request):
    return render(request, 'core/home.html')

@login_required
def doctor_list_view(request):
    doctors = Doctor.objects.all().order_by('name')
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

@login_required
def book_appointment(request, doctor_id):
    """রোগী তার সমস্যা লিখে বুক করবে"""
    if request.method == "POST":
        doctor = get_object_or_404(Doctor, id=doctor_id)
        problem = request.POST.get('problem_description')
        Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            problem_description=problem,
            status='Pending'
        )
        messages.success(request, "আপনার সমস্যাটি ডাক্তারের কাছে পাঠানো হয়েছে।")
        return redirect('home')
    return redirect('doctor_list')

@login_required
def view_my_prescriptions(request):
    """রোগী তার নিজের সব প্রেসক্রিপশন এবং এআই এনালাইসিস দেখবে"""
    prescriptions = Prescription.objects.filter(patient=request.user).order_by('-created_at')
    return render(request, 'core/view_prescriptions.html', {'prescriptions': prescriptions})

@login_required
def prescription_detail_ai(request, pk):
    """নির্দিষ্ট প্রেসক্রিপশনের এআই বিশ্লেষণ"""
    prescription = get_object_or_404(Prescription, pk=pk, patient=request.user)
    # যদি আগে বিশ্লেষণ না করা থাকে তবে এআই ইঞ্জিন কল করবে
    if not prescription.ai_analysis:
        analysis = extract_text_and_analyze(None, prescription.medicines)
        prescription.ai_analysis = analysis
        prescription.save()
    return render(request, 'core/view_prescription.html', {'prescription': prescription})

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 03: ADMIN INTERFACE (PATIENT LIST & PRESCRIPTION CREATION)
# ────────────────────────────────────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_superuser)
def admin_patient_list(request):
    """অ্যাডমিন সব রোগীর লিস্ট দেখবে"""
    appointments = Appointment.objects.all().order_by('-created_at')
    return render(request, 'core/admin_patient_list.html', {'appointments': appointments})

@user_passes_test(lambda u: u.is_superuser)
def create_prescription_view(request, appt_id):
    """অ্যাডমিন রোগীর সমস্যা দেখে প্রেসক্রিপশন লিখবে"""
    appointment = get_object_or_404(Appointment, id=appt_id)
    if request.method == "POST":
        medicines = request.POST.get('medicines')
        advice = request.POST.get('advice')
        Prescription.objects.create(
            appointment=appointment,
            patient=appointment.patient,
            medicines=medicines,
            advice=advice
        )
        appointment.status = 'Approved'
        appointment.save()
        messages.success(request, "প্রেসক্রিপশন সফলভাবে পাঠানো হয়েছে।")
        return redirect('admin_patient_list')
    return render(request, 'core/create_prescription.html', {'appointment': appointment})

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 04: AI & MISC (BLOOD BANK, SERVICES)
# ────────────────────────────────────────────────────────────────────────────────

def service_list_view(request):
    services = HospitalService.objects.all().order_by('service_name')
    return render(request, 'core/service_list.html', {'services': services})

def blood_bank_view(request):
    donors = BloodDonor.objects.all().order_by('blood_group')
    return render(request, 'core/blood_bank.html', {'donors': donors})

@login_required
def ai_agent_page(request):
    return render(request, 'core/ai_agent.html')

def ask_ai(request):
    if request.method == "POST":
        user_message = request.POST.get('message', '').strip()
        if not user_message:
            return JsonResponse({'reply': "দয়া করে কিছু টাইপ করুন।"})
        reply = process_ai_command(request.user, user_message, OPENROUTER_API_KEY, MODEL_NAME, SYSTEM_PROMPT)
        return JsonResponse({'reply': reply})
    return JsonResponse({'error': 'Invalid'}, status=400)

@user_passes_test(lambda u: u.is_superuser)
def manual_update_redirect(request, model_name):
    if model_name == 'service': return redirect('/admin/core/hospitalservice/')
    elif model_name == 'doctor': return redirect('/admin/core/doctor/')
    elif model_name == 'donor': return redirect('/admin/core/blooddonor/')
    return redirect('ai_agent')