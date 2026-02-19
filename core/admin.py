from django.contrib import admin
from .models import Doctor, BloodDonor, PatientProfile

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'rating', 'schedule', 'is_available')
    search_fields = ('name', 'specialty')
    list_editable = ('rating', 'schedule', 'is_available')

@admin.register(BloodDonor)
class BloodDonorAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'blood_group', 'last_donation_date', 'total_bags_donated', 'contact')
    list_filter = ('blood_group',)
    search_fields = ('donor_name', 'contact')

@admin.register(PatientProfile)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile_number')