from django.contrib import admin
from .models import Doctor, BloodDonor, PatientProfile, HospitalService

# ────────────────────────────────────────────────
# Hospital Services & Billing Admin
# ────────────────────────────────────────────────
@admin.register(HospitalService)
class HospitalServiceAdmin(admin.ModelAdmin):
    """সার্ভিস ও বিলিং ম্যানেজমেন্টের জন্য অ্যাডমিন ইন্টারফেস"""
    list_display = ('service_name', 'price', 'category', 'last_updated')
    list_filter = ('category',)
    search_fields = ('service_name', 'category')
    list_editable = ('price', 'category') # সরাসরি লিস্ট থেকে দাম পরিবর্তন করার সুবিধা
    ordering = ('service_name',)
    list_per_page = 20

# ────────────────────────────────────────────────
# Doctor Management Admin
# ────────────────────────────────────────────────
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """ডাক্তারদের তথ্য ম্যানেজমেন্ট"""
    list_display = ('name', 'specialty', 'rating', 'schedule', 'is_available')
    search_fields = ('name', 'specialty')
    list_editable = ('rating', 'schedule', 'is_available')
    list_filter = ('specialty', 'is_available')
    ordering = ('name',)

# ────────────────────────────────────────────────
# Blood Bank Admin
# ────────────────────────────────────────────────
@admin.register(BloodDonor)
class BloodDonorAdmin(admin.ModelAdmin):
    """রক্তদাতাদের ডাটাবেস ম্যানেজমেন্ট"""
    list_display = ('donor_name', 'blood_group', 'last_donation_date', 'total_bags_donated', 'contact')
    list_filter = ('blood_group',)
    search_fields = ('donor_name', 'contact')
    ordering = ('-last_donation_date',) # সর্বশেষ ডোনারকে আগে দেখাবে

# ────────────────────────────────────────────────
# Patient Profile Admin
# ────────────────────────────────────────────────
@admin.register(PatientProfile)
class PatientAdmin(admin.ModelAdmin):
    """রোগীদের প্রোফাইল ম্যানেজমেন্ট"""
    list_display = ('full_name', 'mobile_number')
    search_fields = ('full_name', 'mobile_number')