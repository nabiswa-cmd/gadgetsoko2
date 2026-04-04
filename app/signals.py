from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import UserActivity

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        action='LOGIN',
        extra_info='User logged in via Gmail'
    )

# app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:  # Only send if the user was just created
        subject = f"Welcome to Gadget Soko, {instance.username}!"
        message = "Thank you for creating an account with us. Happy shopping!"
        send_mail(subject, message, None, [instance.email])