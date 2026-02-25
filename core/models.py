from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 01: USER & BASIC INFO
# ────────────────────────────────────────────────────────────────────────────────

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return f"{self.full_name} ({self.mobile_number})"

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100) 
    schedule = models.TextField() 
    rating = models.FloatField(default=5.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    experience_years = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.name} - {self.specialty}"

class BloodDonor(models.Model):
    donor_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=5)
    contact = models.CharField(max_length=15)
    last_donation_date = models.DateField(null=True, blank=True)
    total_bags_donated = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.donor_name} ({self.blood_group})"

class HospitalService(models.Model):
    service_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} - {self.price} BDT"

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 02: APPOINTMENT, RECORD & PRESCRIPTION (NEWLY INTEGRATED)
# ────────────────────────────────────────────────────────────────────────────────

class Appointment(models.Model):
    """রোগীর বুকিং এবং সমস্যার বিবরণ"""
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    problem_description = models.TextField() # রোগী তার সমস্যা লিখবে
    status = models.CharField(max_length=20, default='Pending') # Pending, Approved, Completed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appt: {self.patient.username} with {self.doctor.name}"

class Prescription(models.Model):
    """ডাক্তারের দেওয়া প্রেসক্রিপশন"""
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    medicines = models.TextField() # ওষুধের নাম ও ডোজ
    advice = models.TextField() # ডাক্তারের পরামর্শ
    ai_analysis = models.TextField(blank=True, null=True) # AI থেকে পাওয়া ওষুধের নিয়ম
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.patient.username} - {self.created_at.date()}"

class PatientRecord(models.Model):
    """পুরানো প্রেসক্রিপশন বা ল্যাব রিপোর্টের ছবি/ফাইল"""
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    record_file = models.FileField(upload_to='patient_records/') # মিডিয়া ফোল্ডারে সেভ হবে
    extracted_text = models.TextField(blank=True, null=True) # AI ইমেজ থেকে যা পড়বে
    is_analyzed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Record: {self.patient.username} ({self.uploaded_at.date()})"