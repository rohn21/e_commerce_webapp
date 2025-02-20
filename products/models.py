from django.db import models
from django.contrib.auth import get_user_model
from requests import delete

from utils.custom_functions import get_product_image
from django.utils.translation import gettext_lazy as _

User = get_user_model()


# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'category'

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sub_category'

    def __str__(self):
        return self.name


# could be added custom_product_id
class Product(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='products')
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    available_quantity = models.IntegerField(blank=True, null=True)
    image = models.ImageField(upload_to=get_product_image, blank=True, null=True)

    class Meta:
        db_table = 'product'

    def __str__(self):
        return self.name


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='carts')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.user.username}'s cart"

class Coupon(models.Model):
    # review
    DISCOUNT_TYPE = [
        ('fixed', 'Fixed amount'),
        ('percentage', 'Percentage'),
    ]

    coupon_code = models.CharField(max_length=12, unique=True)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    max_discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    discount_type = models.CharField(max_length=30, choices=DISCOUNT_TYPE)
    usage = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupon'

    def __str__(self):
        return self.coupon_code

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address')
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=300)
    state = models.CharField(max_length=150)
    pincode = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'address'

    def __str__(self):
        return self.user.username

class ShippingMethod(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    description = models.TextField()

    class Meta:
        db_table = 'shipping_method'

    def __str__(self):
        return self.name

# can generate order_id
class Order(models.Model):
    CHECKOUT = 'CH'
    SHIPPED = 'S'
    DELIVERED = 'D'
    CANCELLED = 'CN'

    ORDER_STATUS = [
        (CHECKOUT, 'Checkout'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, related_name='orders', blank=True, null=True)
    total_price = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, blank=True, null=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, blank=True, null=True)
    payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_session_id = models.CharField(max_length=200, blank=True, null=True)
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name='orders', blank=True,null=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='orders', blank=True, null=True)
    tracking_number = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order'

    def __str__(self):
        return f"{self.user.username} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price = models.PositiveIntegerField()

    class Meta:
        db_table = 'order_item'

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.product.user.username}'s order"

class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'rating'

    def __str__(self):
        return self.rating

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlists')

    class Meta:
        db_table = 'wishlist'

    def __str__(self):
        return f"{self.product.name} - {self.product.ratings}"

