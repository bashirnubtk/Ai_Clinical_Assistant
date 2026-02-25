"""
WSGI config for CareNexus project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# প্রজেক্টের সেটিংস মডিউল সেট করা হচ্ছে
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CareNexus.settings')

# সার্ভার অ্যাপ্লিকেশন ভেরিয়েবল
application = get_wsgi_application()