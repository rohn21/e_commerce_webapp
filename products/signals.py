from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Product, Order, CartItem, OrderItem, Coupon

User = get_user_model()


@receiver(pre_save, sender=Coupon)
def invalidate_expired_coupons(sender, instance, **kwargs):
    """Invalidate expired coupons before saving them."""
    if instance.expires_at < timezone.now():
        instance.is_active = False  # No need to call `save()`

    # This prevents recursion because pre_save fires before saving, so there's no need to call save() inside the signal.


@receiver(pre_save, sender=Order)
def order_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
        except Order.DoesNotExist:
            return None

        if old_instance.status != instance.status:
            if instance.status == Order.SHIPPED:
                print("Order is Shipped.")


@receiver(pre_save, sender=Order)
def payment_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
        except Order.DoesNotExist:
            return None

        if old_instance.payment_status != instance.payment_status:
            if instance.payment_status == 'pending':
                print("Payment is pending.")


# @receiver(pre_save, sender=Order)
# def update_order_total(sender, instance, **kwargs):
#     """Updates the order total before saving."""
#     if instance.pk is None:  # Only for new orders
#         total = 0
#         for item in instance.order_items.all():
#             total += item.product.price * item.quantity
#         instance.total_amount = total
#
#         if instance.coupon:
#             if instance.coupon.valid_until >= timezone.now():
#                 discount = instance.coupon.discount
#                 if instance.coupon.discount_type == 'percentage':
#                     instance.total_amount -= (total * discount / 100)
#                 elif instance.coupon.discount_type == 'fixed':
#                     instance.total_amount -= discount
#             else:
#                 instance.coupon = None  # coupon expired.
#                 instance.save()
