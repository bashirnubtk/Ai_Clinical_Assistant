import requests
import re
from django.conf import settings
from .models import Doctor, BloodDonor, HospitalService, PatientProfile, Prescription, Appointment

def process_ai_command(user, user_message, api_key, model_name, system_prompt):
    """
    CareNexus AI Engine: এটি ডাটাবেস থেকে রিয়েল-টাইম তথ্য সংগ্রহ করে এআই-কে প্রদান করে।
    """
    user_message_lower = user_message.lower()
    
    # --- সেকশন ১: অ্যাডমিন কন্ট্রোল (ডাটাবেস আপডেট ও ডিলিট) ---
    if user.is_superuser:
        # ডিলিট লজিক
        if any(w in user_message for w in ["ডিলিট", "রিমুভ", "বাদ দাও", "মুছে ফেলো"]):
            clean_name = re.sub(r'ডিলিট|রিমুভ|বাদ দাও|মুছে|ফেলো|করো|সার্ভিস|তালিকা', '', user_message).strip()
            if clean_name:
                deleted_count, _ = HospitalService.objects.filter(service_name__icontains=clean_name).delete()
                if deleted_count > 0:
                    return f"জি অ্যাডমিন, আমি সফলভাবে '{clean_name}' সংক্রান্ত সকল তথ্য ডাটাবেস থেকে মুছে দিয়েছি।"
                else:
                    return f"দুঃখিত অ্যাডমিন, '{clean_name}' নামে কোনো সার্ভিস আমি খুঁজে পাইনি।"

        # অ্যাড বা আপডেট লজিক
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
                status = "তৈরি" if created else "আপডেট"
                return f"জি অ্যাডমিন, '{target_service}' এর মূল্য {new_amount} ৳ হিসেবে {status} করা হয়েছে।"

    # --- সেকশন ২: ডাটা রিট্রিভাল (এআই-কে ডাটাবেস নলেজ দেওয়া) ---
    database_info = ""

    # ১. ডাক্তার ও স্পেশালিটি তথ্য
    if any(word in user_message_lower for word in ["ডাক্তার", "ডক্টর", "doctor", "specialist", "ব্যথা", "অসুখ"]):
        docs = Doctor.objects.all()
        if docs.exists():
            database_info += "\n[ডাক্তারদের তালিকা ও শিডিউল]:\n"
            database_info += "\n".join([f"- {d.name} ({d.specialty}), সময়: {d.schedule}" for d in docs])
        else:
            database_info += "\nদুঃখিত, বর্তমানে কোনো ডাক্তারের তথ্য ডাটাবেসে নেই।"

    # ২. রক্তদাতা ও ব্লাড গ্রুপ তথ্য
    if any(word in user_message_lower for word in ["রক্ত", "ব্লাড", "blood", "donor", "দাতা"]):
        donors = BloodDonor.objects.all()
        if donors.exists():
            database_info += "\n[রক্তদাতাদের তালিকা]:\n"
            database_info += "\n".join([f"- {b.donor_name}, গ্রুপ: {b.blood_group}, ফোন: {b.contact}" for b in donors])
        else:
            database_info += "\nবর্তমানে কোনো রক্তদাতা নেই।"

    # ৩. হাসপাতালের সার্ভিস ও টেস্টের খরচ
    if any(word in user_message_lower for word in ["খরচ", "বিল", "টেস্ট", "মূল্য", "টাকা", "সার্ভিস"]):
        services = HospitalService.objects.all()
        if services.exists():
            database_info += "\n[সার্ভিস ও টেস্টের মূল্য তালিকা]:\n"
            database_info += "\n".join([f"- {s.service_name}: {s.price} ৳" for s in services])
        else:
            database_info += "\nসার্ভিসের মূল্য তালিকা পাওয়া যায়নি।"

    # ৪. অ্যাডমিন যখন রোগী বা অ্যাপয়েন্টমেন্ট সম্পর্কে জানতে চায়
    if user.is_superuser and any(word in user_message_lower for word in ["রোগী", "পেশেন্ট", "patient", "অ্যাপয়েন্টমেন্ট"]):
        patients = PatientProfile.objects.all()
        appts = Appointment.objects.all().order_by('-created_at')[:5]
        database_info += f"\n[অ্যাডমিন তথ্য]: মোট নিবন্ধিত রোগী {patients.count()} জন।\n"
        database_info += "সাম্প্রতিক অ্যাপয়েন্টমেন্ট: " + ", ".join([f"{a.patient.username} with {a.doctor.name}" for a in appts])

    # --- সেকশন ৩: এপিআই কল (সংবেদনশীল উত্তর তৈরি) ---
    # যদি ডাটাবেস থেকে কোনো তথ্য পাওয়া যায়, তবে সেটি প্রম্পটে ইনজেক্ট করা হবে
    if database_info:
        final_user_prompt = f"হাসপাতাল ডাটাবেস তথ্য:\n{database_info}\n\nইউজারের প্রশ্ন: {user_message}\n\nনির্দেশনা: উপরের তথ্য ব্যবহার করে একজন দক্ষ দয়ালু চিকিৎসকের মতো উত্তর দিন।"
    else:
        final_user_prompt = f"ইউজারের প্রশ্ন: {user_message}\n\nনির্দেশনা: ইউজার সাধারণ কথা বলেছে। সৌজন্যমূলক মানুষের মতো উত্তর দিন।"

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_user_prompt},
                ],
                "temperature": 0.7, # সামান্য বাড়ানো হয়েছে সৃজনশীলতার জন্য
            },
            timeout=25
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error: {str(e)}")
        return "আমি দুঃখিত, সার্ভারের সাথে সংযোগ বিচ্ছিন্ন হয়েছে। দয়া করে ফ্রন্ট ডেস্কে কথা বলুন।"