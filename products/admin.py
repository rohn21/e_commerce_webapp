from django.contrib import admin
from .models import (Category, Subcategory,
                     Product, CartItem,
                    Order, OrderItem,
                    Wishlist,
                    Address,
                     Rating)
# Register your models here.

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Product)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Wishlist)
admin.site.register(Rating)