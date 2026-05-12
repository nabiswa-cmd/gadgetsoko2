import requests
import logging
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import UserProfile

logger = logging.getLogger(__name__)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        """
        Called when a social account user is saved (new OR existing).
        Captures Google profile picture and sends welcome email for new users.
        """
        # Track whether this is a brand-new user BEFORE super() creates them
        is_new = sociallogin.is_existing is False

        user = super().save_user(request, sociallogin, form)

        # Mark as social auth so the post_save signal skips the welcome email
        user._from_social_auth = True

        # Ensure UserProfile exists
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Download and save Google avatar if they don't have one yet
        if not profile.avatar:
            try:
                extra_data = sociallogin.account.extra_data
                picture_url = extra_data.get('picture')

                if picture_url:
                    resp = requests.get(picture_url, timeout=10)
                    resp.raise_for_status()

                    content_type = resp.headers.get('Content-Type', 'image/jpeg')
                    ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[-1]
                    filename = f"google_{user.pk}.{ext}"

                    profile.avatar.save(filename, ContentFile(resp.content), save=True)
                    logger.info("Saved Google avatar for user %s", user.username)

            except Exception as exc:
                logger.warning("Could not save Google avatar for %s: %s", user.username, exc)

        # Send welcome email only for brand-new users, AFTER avatar is saved
        if is_new and user.email:
            _send_welcome_email(user, profile)

        return user

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        """Populate basic user fields from Google data."""
        user = super().populate_user(request, sociallogin, data)
        return user

    def pre_social_login(self, request, sociallogin):
        """Fires on every Google login. Refreshes avatar if it was deleted."""
        if not sociallogin.is_existing:
            return  # new user — handled in save_user

        try:
            user = sociallogin.user
            if not user.pk:
                return
            profile, _ = UserProfile.objects.get_or_create(user=user)

            if not profile.avatar:
                picture_url = sociallogin.account.extra_data.get('picture')
                if picture_url:
                    resp = requests.get(picture_url, timeout=10)
                    resp.raise_for_status()
                    content_type = resp.headers.get('Content-Type', 'image/jpeg')
                    ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[-1]
                    profile.avatar.save(
                        f"google_{user.pk}.{ext}",
                        ContentFile(resp.content),
                        save=True
                    )
        except Exception as exc:
            logger.warning("pre_social_login avatar refresh failed: %s", exc)


# ─────────────────────────────────────────────────────────────────
# Standalone welcome email — called after avatar is already saved
# (mirrors the HTML in signals.py but runs from the adapter)
# ─────────────────────────────────────────────────────────────────
def _build_avatar_html(profile, protocol, domain) -> str:
    avatar_url = None
    try:
        if profile and profile.avatar and profile.avatar.name:
            avatar_url = f"{protocol}://{domain}{profile.avatar.url}"
    except Exception:
        avatar_url = None

    if avatar_url:
        return f"""
        <img src="{avatar_url}"
             alt="Profile photo" width="80" height="80"
             style="border-radius:50%;object-fit:cover;
                    border:3px solid #f4330c;display:block;">
        """
    initial = (profile.user.username[0] if profile and profile.user.username else "?").upper()
    return f"""
    <div style="width:80px;height:80px;border-radius:50%;
                background:linear-gradient(135deg,#f4330c,#ff8c00);
                display:flex;align-items:center;justify-content:center;
                border:3px solid #f4330c;font-size:34px;font-weight:900;
                color:#ffffff;font-family:'Segoe UI',Arial,sans-serif;
                text-transform:uppercase;margin:0 auto;">
        {initial}
    </div>
    """


def _send_welcome_email(user, profile):
    protocol = "https"
    domain   = getattr(settings, "SITE_DOMAIN", "gadgetsoko.com")
    avatar_html  = _build_avatar_html(profile, protocol, domain)
    display_name = user.get_full_name() or user.username

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background-color:#ffffff;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#ffffff;">
    <tr>
      <td align="center">
        <table border="0" cellpadding="0" cellspacing="0" width="500" style="background-color:#ffffff;">

          <!-- LOGO -->
          <tr>
            <td align="center" style="padding:40px 0 20px 0;border-bottom:2px solid #f4330c;">
              <img src="{protocol}://{domain}/static/images/android-chrome-512x512.png"
                   alt="Gadget Soko" width="140" style="display:block;border:0;">
            </td>
          </tr>

          <!-- AVATAR + GREETING -->
          <tr>
            <td align="center" style="padding:40px 20px 10px 20px;">
              {avatar_html}
              <h2 style="color:#0b3a63;font-size:22px;margin:18px 0 6px 0;
                         font-weight:bold;text-transform:uppercase;letter-spacing:2px;">
                Welcome, {display_name}!
              </h2>
              <p style="color:#64748b;font-size:13px;margin:0;">@{user.username}</p>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:24px 30px 40px 30px;text-align:center;">
              <p style="color:#1e293b;font-size:15px;line-height:26px;margin:0 0 30px 0;">
                Your account at <strong>Gadget Soko</strong> is now active.<br>
                You are ready to explore the latest innovations in tech —
                laptops, phones, accessories and more, all at unbeatable prices.
              </p>
              <a href="{protocol}://{domain}"
                 style="background-color:#f4330c;color:#ffffff;padding:16px 42px;
                        text-decoration:none;font-size:13px;font-weight:bold;
                        display:inline-block;text-transform:uppercase;letter-spacing:2px;">
                Start Shopping
              </a>
              <p style="margin:28px 0 0 0;font-size:12px;color:#94a3b8;">
                <a href="{protocol}://{domain}/products/" style="color:#f4330c;text-decoration:none;">Browse Products</a>
                &nbsp;&bull;&nbsp;
                <a href="{protocol}://{domain}/profile/edit/" style="color:#f4330c;text-decoration:none;">Complete Your Profile</a>
                &nbsp;&bull;&nbsp;
                <a href="{protocol}://{domain}/#contacts" style="color:#f4330c;text-decoration:none;">Contact Us</a>
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:30px 20px;border-top:1px solid #e2e8f0;text-align:center;">
              <p style="color:#64748b;font-size:11px;margin:0;text-transform:uppercase;letter-spacing:1px;">
                &copy; 2026 GADGET SOKO | TECH &amp; RETAIL<br>
                <span style="display:block;margin-top:6px;color:#94a3b8;">
                  Laxmi Plaza, CBD &mdash; Biashara Street, Shop No. 5, Nairobi, Kenya
                </span>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    plain_text = (
        f"Welcome to Gadget Soko, {display_name}!\n\n"
        f"Your account (@{user.username}) is now active.\n\n"
        f"Start shopping: {protocol}://{domain}\n"
        f"Complete your profile: {protocol}://{domain}/profile/edit/\n\n"
        f"© 2026 Gadget Soko | Nairobi, Kenya"
    )

    try:
        msg = EmailMultiAlternatives(
            subject=f"Welcome to Gadget Soko, {display_name}! 🎉",
            body=plain_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info("Welcome email sent to %s", user.email)
    except Exception as exc:
        logger.exception("Welcome email failed for user %s: %s", user.username, exc)