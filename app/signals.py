from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import UserActivity
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        action='LOGIN',
        extra_info='User logged in via Gmail'
    )

# app/signals.py


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        subject = f"Welcome to Gadget Soko, {instance.username}! 🎉"
        
        # Define context for the template
        context = {
            'username': instance.username,
            'domain': 'gadgetsoko.com', # Replace with your actual domain
            'protocol': 'https',
        }

        # Render HTML and create plain-text fallback
        html_content = render_to_string('emails/welcome_email.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()