from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from datetime import timezone
from .models import Product, Order, CartItem, OrderItem, Coupon


User = get_user_model()

@receiver(post_save, sender=Coupon)
def invalidate_expired_coupons(sender, instance, **kwargs):
    """Invalidates expired coupons."""
    if instance.expires_at < timezone.now():
        instance.is_active = False
        instance.save()