from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accounts.models import Profile
from allauth.account.utils import send_email_confirmation
from allauth.account.signals import user_signed_up

User = get_user_model()


@receiver(user_signed_up)
def send_email_confirmation_on_register(request, user, **kwargs):
    print("Signal called!!!")
    if request:
        print(f"Request: {request}")
    if user:
        print(f"User: {user.email}")
    send_email_confirmation(request, user)


# user-profile
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# @receiver(post_save, sender=User)
# def save_profile(sender, instance, **kwargs):
#     instance.profiles.save()
