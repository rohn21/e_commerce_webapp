from django.urls import path
from products.views import (CategoryViewSet, SubCategoryViewSet,
                            AddProductAPIView, ProductDetailAPIView,
                            ProductRatingAPIView,
                            CartView, CartItemDetailView, ClearCartView,
                            OrderCheckoutView, OrderHistioryView, OrderDetailView,
                            WishlistAPIView, PaymentSuccessView, payment_cancel,
                            CheckoutPage, CouponAPIView)
from rest_framework.routers import DefaultRouter

app_name = 'products'

router = DefaultRouter()
router.register(r'category', CategoryViewSet, basename='category')
router.register(r'sub-category', SubCategoryViewSet, basename='subcategory')
router.register(r'wishlist', WishlistAPIView, basename='wishlist')
router.register(r'coupon', CouponAPIView, basename='coupon')

urlpatterns = [
    # product
    path('add-product/', AddProductAPIView.as_view(), name='list-create-product'),
    path('product/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),

    # cart
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:product_id>/', CartItemDetailView.as_view(), name='cart-item'),
    path('cart/clear/', ClearCartView.as_view(), name='remove-cart_item'),

    # order-history
    path('checkout/', OrderCheckoutView.as_view(), name='checkout'),
    # path('cart/checkout/', CheckoutPage.as_view(), name='checkout-page'),
    path('order/history/', OrderHistioryView.as_view(), name='order-history'),
    path('order/details/<int:pk>/', OrderDetailView.as_view(), name='order-details'),

    # payment
    path('payment/success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/cancel/', payment_cancel, name= 'payment_cancel'),

    # product-rating
    path('ratings/', ProductRatingAPIView.as_view(), name='ratings'),
]
urlpatterns += router.urls

