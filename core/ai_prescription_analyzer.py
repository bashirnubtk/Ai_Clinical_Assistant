import requests
import base64
from django.conf import settings

def extract_text_and_analyze(file_path, patient_history):
    # ইমেজ ফাইলকে Base64 এ কনভার্ট করা (Vision API এর জন্য)
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    # OpenRouter বা Vision API ব্যবহার করে ছবি বিশ্লেষণ
    headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
    payload = {
        "model": "google/gemini-flash-1.5-vision", # ভিশন মডেল যা ছবি পড়তে পারে
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"এই প্রেসক্রিপশনের ছবি থেকে সব ওষুধের নাম এবং নিয়ম বের করুন। রোগীর পূর্বের ইতিহাস ছিল: {patient_history}. এই দুটির মধ্যে সমন্বয় করে বাংলায় পরামর্শ দিন।"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}
                ]
            }
        ]
    }
    
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']