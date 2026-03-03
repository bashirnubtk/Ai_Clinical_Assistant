import requests
import base64
import os
from django.conf import settings
from .models import Prescription

def extract_text_and_analyze(file_path, user_message, user):
    """
    ছবি থাকলে Vision মডেল এবং না থাকলে Text মডেল ব্যবহার করে বিশ্লেষণ করবে।
    সাথে ইউজারের বিস্তারিত মেডিকেল ইতিহাস চেক করবে।
    """
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
    }

    # ১. ডাটাবেজ থেকে এই ইউজারের শেষ ৩টি প্রেসক্রিপশন বিস্তারিতভাবে আনা
    user_prescriptions = Prescription.objects.filter(patient=user).order_by('-created_at')[:3]
    
    # ২. প্রেসক্রিপশন থাকলে সেগুলো টেক্সট আকারে সাজানো
    history_context = ""
    if user_prescriptions.exists():
        history_context = "আপনার মেডিকেল ইতিহাস (আগের রেকর্ড):\n"
        for p in user_prescriptions:
            # তারিখ ফরম্যাট করা (যেমন: Feb 25, 2026)
            date_str = p.created_at.strftime("%b %d, %Y")
            history_context += f"- তারিখ: {date_str}, ঔষধ: {p.medicines}, পরামর্শ: {p.advice}\n"
    else:
        history_context = "আপনার কোনো আগের প্রেসক্রিপশন ডাটাবেজে পাওয়া যায়নি।"

    # ৩. সিস্টেম ইনস্ট্রাকশন ও ফুল প্রম্পট
    system_instruction = (
        "আপনি কেয়ারনেক্সাস স্মার্ট এআই (CareNexus AI Robot)। আপনি অত্যন্ত আন্তরিক ও পেশাদার।"
        "যদি রোগী ছবি দেয়, তবে ছবি থেকে ঔষধ ও পরামর্শ সহজভাবে বুঝিয়ে বলুন।"
        "যদি ছবি না দেয়, তবে তার শারীরিক সমস্যার কথা শুনে প্রাথমিক পরামর্শ দিন।"
        "নিচে দেওয়া রোগীর ইতিহাসটি ভালভাবে পড়ে সেই অনুযায়ী সামঞ্জস্যপূর্ণ উত্তর দিন।"
    )

    # ৪. কন্টেন্ট এবং মডেল নির্বাচন
    # যদি ছবি না থাকে
    if not file_path or not os.path.exists(file_path):
        model_name = "meta-llama/llama-3.1-8b-instruct"
        content = f"{system_instruction}\n\n{history_context}\n\nইউজারের বর্তমান প্রশ্ন: {user_message}\n\nউপরের ইতিহাসের ভিত্তিতে উত্তর দিন।"
        messages = [{"role": "user", "content": content}]
    
    # যদি ছবি থাকে
    else:
        model_name = "google/gemini-flash-1.5-vision"
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": f"{system_instruction}\n\n{history_context}\n\nইউজারের প্রশ্ন/ইতিহাস: {user_message}\n\nউপরের সব তথ্যের ভিত্তিতে ছবি বিশ্লেষণ করুন।"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}
                    }
                ]
            }
        ]

    # ৫. এপিআই কল
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.5 # রেজাল্ট আরও কনসিস্টেন্ট রাখার জন্য একটু কমানো হয়েছে
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions", 
            headers=headers, 
            json=payload, 
            timeout=40
        )
        response_data = response.json()
        
        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content']
        else:
            return f"এআই সার্ভার ত্রুটি: {response_data.get('error', {}).get('message', 'Unknown Error')}"
            
    except Exception as e:
        return f"দুঃখিত, আমি এই মুহূর্তে সংযুক্ত হতে পারছি না। সমস্যা: {str(e)}"