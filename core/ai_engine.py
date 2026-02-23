import requests
import re
from django.http import JsonResponse
from .models import Doctor, BloodDonor, HospitalService, PatientProfile

# --------------------------------------------------------------------------------
# AI CORE ENGINE: ডাটাবেস আপডেট, ডিলিট এবং চ্যাট কন্ট্রোল
# --------------------------------------------------------------------------------

def process_ai_command(user, user_message, api_key, model_name, system_prompt):
    """
    এই ফাংশনটি ইউজারের মেসেজ বিশ্লেষণ করে ডাটাবেস আপডেট করবে অথবা এআই এর মাধ্যমে উত্তর দেবে।
    """
    user_message_lower = user_message.lower()
    
    # --- সেকশন ১: অ্যাডমিন কমান্ড হ্যান্ডলিং (নিখুঁত ডাটাবেস রাইটিং) ---
    if user.is_superuser:
        
        # ১.১ ডিলিট লজিক (নাম খুঁজে বের করে ডিলিট করা)
        if any(w in user_message for w in ["ডিলিট", "রিমুভ", "বাদ দাও", "মুছে ফেলো"]):
            # কমান্ডের শব্দগুলো বাদ দিয়ে আসল নাম বের করা
            clean_name = re.sub(r'ডিলিট|রিমুভ|বাদ দাও|মুছে|ফেলো|করো|সার্ভিস|তালিকা', '', user_message).strip()
            if clean_name:
                deleted_count, _ = HospitalService.objects.filter(service_name__icontains=clean_name).delete()
                if deleted_count > 0:
                    return f"কেয়ারনেক্সাস এআই: অ্যাডমিন, আমি সফলভাবে '{clean_name}' সংক্রান্ত সকল এন্ট্রি ডাটাবেস থেকে মুছে দিয়েছি।"
                else:
                    return f"কেয়ারনেক্সাস এআই: দুঃখিত অ্যাডমিন, '{clean_name}' নামে কোনো সার্ভিস আমার ডাটাবেসে নেই।"

        # ১.২ অ্যাড বা আপডেট লজিক (নিখুঁত মূল্য ও ডুপ্লিকেট রোধ)
        price_match = re.search(r'(\d+)', user_message)
        if price_match:
            new_amount = price_match.group(1)
            
            # নাম ফিল্টার করার সময় সতর্কতা: 'টাকা', 'আপডেট' ইত্যাদি বাদ দিয়ে আসল নাম রাখা
            target_service = user_message
            words_to_remove = [new_amount, "টাকা", "বিল", "খরচ", "সেট", "করো", "মূল্য", "৳", "আপডেট", "হিসাব", "অ্যাড"]
            for word in words_to_remove:
                target_service = target_service.replace(word, "")
            
            target_service = target_service.strip() # বাড়তি স্পেস মুছে ফেলা

            if target_service:
                # update_or_create নিশ্চিত করা
                obj, created = HospitalService.objects.update_or_create(
                    service_name__iexact=target_service,
                    defaults={
                        'service_name': target_service, # সার্ভিস নাম আপডেট বা তৈরি
                        'price': new_amount,
                        'category': 'SERVICE'
                    }
                )
                action_type = "নতুন এন্ট্রি তৈরি" if created else "মূল্য আপডেট"
                return f"কেয়ারনেক্সাস এআই: জি অ্যাডমিন, '{target_service}' সার্ভিসের {action_type} সফল হয়েছে। বর্তমান মূল্য: {new_amount} ৳।"

    # --- সেকশন ২: ডাটা রিট্রিভাল (Context Building for Patient) ---
    # রোগীকে উত্তর দেওয়ার আগে ডাটাবেস থেকে তথ্য নেওয়া
    database_context = "CareNexus হাসপাতালের বর্তমান ডাটাবেস তথ্য:\n"
    
    # ডাক্তারদের ইনফরমেশন
    if any(word in user_message_lower for word in ["ডাক্তার", "স্পেশালিস্ট", "বিশেষজ্ঞ", "সমস্যা"]):
        docs = Doctor.objects.all()[:10]
        if docs.exists():
            database_context += "ডাক্তার ও সময়: " + ", ".join([f"{d.name}({d.specialty} - {d.schedule})" for d in docs]) + "\n"
        else:
            database_context += "বর্তমানে কোনো ডাক্তারের তথ্য নেই।\n"

    # রক্তদাতাদের ইনফরমেশন
    if any(word in user_message_lower for word in ["রক্ত", "ব্লাড", "ডোনার", "দাতা"]):
        donors = BloodDonor.objects.all()[:10]
        if donors.exists():
            database_context += "রক্তদাতা তালিকা: " + ", ".join([f"{b.donor_name}({b.blood_group}: {b.contact})" for b in donors]) + "\n"
        else:
            database_context += "দুঃখিত, বর্তমানে কোনো রক্তদাতা খুঁজে পাওয়া যায়নি।\n"

    # টেস্ট ও সার্ভিসের খরচ
    if any(word in user_message_lower for word in ["বিল", "খরচ", "টেস্ট", "সার্ভিস", "মূল্য"]):
        services = HospitalService.objects.all()[:10]
        if services.exists():
            database_context += "সার্ভিস খরচ: " + ", ".join([f"{s.service_name}: {s.price}tk" for s in services]) + "\n"

    # --- সেকশন ৩: এপিআই প্রসেসিং (Final Reply Generation) ---
    try:
        api_payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"হাসপাতাল ডাটা: {database_context}\nইউজার প্রশ্ন: {user_message}"}
            ],
            "temperature": 0.6,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=api_payload,
            timeout=25
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    except Exception as e:
        print(f"Error Log: {str(e)}")
        return "কেয়ারনেক্সাস এআই: দুঃখিত, আমি এখন অনলাইন সার্ভারের সাথে সংযুক্ত হতে পারছি না। তবে আপনি চাইলে ম্যানুয়ালি তথ্য চেক করতে পারেন।"