from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import UserActivity, UserProfile


# ─────────────────────────────────────────────────────────────────
# 1. LOG LOGIN ACTIVITY
# ─────────────────────────────────────────────────────────────────
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        action='LOGIN',
        extra_info='User logged in'
    )


# ─────────────────────────────────────────────────────────────────
# 2. AUTO-CREATE UserProfile FOR EVERY NEW USER
#    (Keep this here — remove the duplicate signal from models.py
#     if you added one there earlier)
# ─────────────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
    else:
        # Ensure existing users always have a profile
        UserProfile.objects.get_or_create(user=instance)


# ─────────────────────────────────────────────────────────────────
# 3. WELCOME EMAIL  (sent only on account creation)
#    — Includes the user's profile picture if they have one,
#      otherwise falls back to a branded initial avatar.
# ─────────────────────────────────────────────────────────────────
def _build_avatar_html(profile, protocol, domain) -> str:
    """
    Returns an <img> tag if the user has uploaded a photo,
    otherwise returns a styled initial-letter circle that
    matches the Gadget Soko brand colours.
    """
    avatar_url = None

    # Try to resolve the absolute URL of the avatar
    try:
        if profile and profile.avatar and profile.avatar.name:
            # profile.avatar.url gives the relative /media/... path
            avatar_url = f"{protocol}://{domain}{profile.avatar.url}"
    except Exception:
        avatar_url = None

    if avatar_url:
        return f"""
        <img src="{avatar_url}"
             alt="Profile photo"
             width="80" height="80"
             style="border-radius:50%;
                    object-fit:cover;
                    border:3px solid #f4330c;
                    display:block;">
        """
    else:
        # Coloured circle with the user's initial
        initial = (profile.user.username[0] if profile and profile.user.username else "?").upper()
        return f"""
        <div style="width:80px;height:80px;
                    border-radius:50%;
                    background:linear-gradient(135deg,#f4330c,#ff8c00);
                    display:flex;align-items:center;justify-content:center;
                    border:3px solid #f4330c;
                    font-size:34px;font-weight:900;
                    color:#ffffff;
                    font-family:'Segoe UI',Arial,sans-serif;
                    text-transform:uppercase;
                    margin:0 auto;">
            {initial}
        </div>
        """


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if not created:
        return

    # Skip if no email address
    if not instance.email:
        return

    # Fetch (or create) the profile — avatar may be empty on brand-new accounts
    profile, _ = UserProfile.objects.get_or_create(user=instance)

    # Build the avatar block
    # For new signups the avatar will almost always be empty, so the
    # initial circle renders. If you later add social-auth that supplies
    # a picture URL you can set profile.avatar before the signal fires.
    protocol = "https"
    domain   = getattr(settings, "SITE_DOMAIN", "gadgetsoko.com")
    avatar_html = _build_avatar_html(profile, protocol, domain)

    display_name = instance.get_full_name() or instance.username

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;
             background-color:#ffffff;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%"
         style="background-color:#ffffff;">
    <tr>
      <td align="center">
        <table border="0" cellpadding="0" cellspacing="0" width="500"
               style="background-color:#ffffff;">

          <!-- ── LOGO ── -->
          <tr>
            <td align="center"
                style="padding:40px 0 20px 0;border-bottom:2px solid #f4330c;">
              <img src="{protocol}://{domain}/static/images/android-chrome-512x512.png"
                   alt="Gadget Soko" width="140"
                   style="display:block;border:0;">
            </td>
          </tr>

          <!-- ── AVATAR + GREETING ── -->
          <tr>
            <td align="center" style="padding:40px 20px 10px 20px;">
              {avatar_html}
              <h2 style="color:#0b3a63;font-size:22px;margin:18px 0 6px 0;
                         font-weight:bold;text-transform:uppercase;
                         letter-spacing:2px;">
                Welcome, {display_name}!
              </h2>
              <p style="color:#64748b;font-size:13px;margin:0;">
                @{instance.username}
              </p>
            </td>
          </tr>

          <!-- ── BODY ── -->
          <tr>
            <td style="padding:24px 30px 40px 30px;text-align:center;">
              <p style="color:#1e293b;font-size:15px;line-height:26px;
                        margin:0 0 30px 0;">
                Your account at <strong>Gadget Soko</strong> is now active.<br>
                You are ready to explore the latest innovations in tech —
                laptops, phones, accessories and more, all at unbeatable prices.
              </p>

              <!-- CTA button -->
              <a href="{protocol}://{domain}"
                 style="background-color:#f4330c;color:#ffffff;
                        padding:16px 42px;text-decoration:none;
                        font-size:13px;font-weight:bold;
                        display:inline-block;text-transform:uppercase;
                        letter-spacing:2px;">
                Start Shopping
              </a>

              <!-- Quick links -->
              <p style="margin:28px 0 0 0;font-size:12px;color:#94a3b8;">
                <a href="{protocol}://{domain}/products/"
                   style="color:#f4330c;text-decoration:none;">Browse Products</a>
                &nbsp;&bull;&nbsp;
                <a href="{protocol}://{domain}/profile/edit/"
                   style="color:#f4330c;text-decoration:none;">Complete Your Profile</a>
                &nbsp;&bull;&nbsp;
                <a href="{protocol}://{domain}/#contacts"
                   style="color:#f4330c;text-decoration:none;">Contact Us</a>
              </p>
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="padding:30px 20px;border-top:1px solid #e2e8f0;
                       text-align:center;">
              <p style="color:#64748b;font-size:11px;margin:0;
                        text-transform:uppercase;letter-spacing:1px;">
                &copy; 2026 GADGET SOKO | TECH &amp; RETAIL<br>
                <span style="display:block;margin-top:6px;color:#94a3b8;">
                  Laxmi Plaza, CBD &mdash; Biashara Street, Shop No. 5,
                  Nairobi, Kenya
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
        f"Your account (@{instance.username}) is now active.\n\n"
        f"Start shopping: {protocol}://{domain}\n"
        f"Complete your profile: {protocol}://{domain}/profile/edit/\n\n"
        f"© 2026 Gadget Soko | Nairobi, Kenya"
    )

    try:
        msg = EmailMultiAlternatives(
            subject=f"Welcome to Gadget Soko, {display_name}! 🎉",
            body=plain_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        # Never let an email failure crash account creation
        import logging
        logging.getLogger(__name__).exception(
            "Welcome email failed for user %s: %s", instance.username, exc
        )