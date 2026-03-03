import requests
import re
from django.conf import settings
from .models import Doctor, BloodDonor, HospitalService, PatientProfile, Prescription, Appointment

def process_ai_command(user, user_message, api_key, model_name, system_prompt):
    """
    CareNexus AI Engine: ডাটাবেস থেকে তথ্য নিয়ে সংবেদনশীল ও মানুষের মতো উত্তর তৈরি করে।
    """
    user_message_lower = user_message.lower()
    
    # --- সেকশন ১: অ্যাডমিন কন্ট্রোল (ডাটাবেস রাইটিং) ---
    if user.is_superuser:
        # ডিলিট লজিক
        if any(w in user_message for w in ["ডিলিট", "রিমুভ", "বাদ দাও", "মুছে ফেলো"]):
            clean_name = re.sub(r'ডিলিট|রিমুভ|বাদ দাও|মুছে|ফেলো|করো|সার্ভিস|তালিকা', '', user_message).strip()
            if clean_name:
                deleted_count, _ = HospitalService.objects.filter(service_name__icontains=clean_name).delete()
                if deleted_count > 0:
                    return f"জি অ্যাডমিন, আমি সফলভাবে '{clean_name}' সংক্রান্ত সকল তথ্য ডাটাবেস থেকে মুছে দিয়েছি। আপনার আর কোনো নির্দেশ আছে?"

        # অ্যাড বা আপডেট লজিক (প্রাইস ডিটেকশন)
        price_match = re.search(r'(\d+)', user_message)
        if price_match:
            new_amount = price_match.group(1)
            target_service = user_message
            words_to_remove = [new_amount, "টাকা", "বিল", "খরচ", "সেট", "করো", "মূল্য", "৳", "আপডেট", "হিসাব", "অ্যাড"]
            for word in words_to_remove:
                target_service = target_service.replace(word, "")
            target_service = target_service.strip()

            if target_service:
                obj, created = HospitalService.objects.update_or_create(
                    service_name__iexact=target_service,
                    defaults={'service_name': target_service, 'price': new_amount, 'category': 'SERVICE'}
                )
                action = "নতুন যোগ করেছি" if created else "আপডেট করেছি"
                return f"জি অ্যাডমিন, আমি '{target_service}' সার্ভিসের মূল্য {new_amount} ৳ হিসেবে {action}। এটি এখন ডাটাবেসে সেভ আছে।"

    # --- সেকশন ২: ডাটা রিট্রিভাল (এআই-এর মেমোরিতে ডাটা দেওয়া) ---
    database_info = "--- হাসপাতালের বর্তমান রেকর্ড ---\n"
    
    # ডাক্তার তথ্য
    docs = Doctor.objects.all()
    if docs.exists():
        database_info += "ডাক্তার ও সময়: " + ", ".join([f"{d.name} ({d.specialty} - {d.schedule})" for d in docs]) + "\n"
    
    # রক্তদাতা তথ্য
    donors = BloodDonor.objects.all()
    if donors.exists():
        database_info += "রক্তদাতা: " + ", ".join([f"{b.donor_name} ({b.blood_group}: {b.contact})" for b in donors]) + "\n"

    # টেস্টের মূল্য
    services = HospitalService.objects.all()
    if services.exists():
        database_info += "টেস্টের মূল্য: " + ", ".join([f"{s.service_name} {s.price}tk" for s in services]) + "\n"

    # --- সেকশন ৩: মানুষের মতো প্রম্পট ডিজাইন ---
    # এআই-কে নির্দেশ দেওয়া হচ্ছে সে যেন ডাটাবেসের তথ্য ব্যবহার করে কিন্তু যান্ত্রিকভাবে নয়
    enriched_prompt = f"""
    আপনি কেয়ারনেক্সাস হাসপাতালের একজন স্মার্ট, দয়ালু এবং পেশাদার সহকারী। 
    
    ইউজারের প্রশ্ন: {user_message}
    
    হাসপাতালের ডাটাবেস থেকে প্রাপ্ত তথ্য:
    {database_info}
    
    নির্দেশনা:
    ১. যদি ইউজার সাধারণ কথা (যেমন: কেমন আছেন, হাই) বলে, তবে অত্যন্ত বিনয়ের সাথে উত্তর দিন।
    ২. যদি ডাটাবেসের তথ্য নিয়ে প্রশ্ন করে, তবে উপরের তালিকা থেকে সঠিক তথ্যটি খুঁজে সুন্দরভাবে বলুন।
    ৩. যদি কোনো তথ্য ডাটাবেসে না থাকে, তবে 'বর্তমানে এই তথ্যটি নেই, আমি কি অন্যভাবে সাহায্য করতে পারি?' - এভাবে বলুন।
    ৪. উত্তরের ভাষা হবে সহজ এবং আধুনিক বাংলা।
    """

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enriched_prompt},
                ],
                "temperature": 0.6,
            },
            timeout=25
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return "দুঃখিত, আমি এই মুহূর্তে সার্ভারের সাথে সংযুক্ত হতে পারছি না। দয়া করে কিছুক্ষণ পর চেষ্টা করুন।"