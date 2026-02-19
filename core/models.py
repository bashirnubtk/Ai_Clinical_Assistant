from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# ১. পেশেন্ট প্রোফাইল (মোবাইল নাম্বার ইউনিক রাখতে)
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return f"{self.full_name} ({self.mobile_number})"

# ২. ডাক্তারদের ইনফরমেশন
class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100) # যেমন: মেডিসিন বিশেষজ্ঞ, কার্ডিওলজিস্ট
    schedule = models.TextField() # যেমন: রবি-মঙ্গল সকাল ১০টা
    rating = models.FloatField(default=5.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    experience_years = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.name} - {self.specialty}"

# ৩. ব্লাড ডোনারের তথ্য
class BloodDonor(models.Model):
    donor_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=5)
    contact = models.CharField(max_length=15)
    last_donation_date = models.DateField(null=True, blank=True)
    total_bags_donated = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.donor_name} ({self.blood_group})"