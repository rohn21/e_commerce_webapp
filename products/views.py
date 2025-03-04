from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics, views, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from accounts.permissions import IsOwnerOrReadonly
from accounts.models import Profile
from products.models import (Category, Subcategory,
                             Product, CartItem, Rating,
                             OrderItem, Order, Wishlist,
                             Coupon, Address, ShippingMethod)
from products.serializers import (CategorySerializer, SubCategorySerializer,
                                  ProductSerializer, ProductRatingSerializer,
                                  CartItemSerializer,
                                  OrderSerializer,
                                  WishlistSerializer, CouponSerializer, AddressSerializer)
from products.filters import ProductFilter, OrderFilter
from utils.custom_functions import generate_tracking_number
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from decimal import Decimal, ROUND_HALF_UP
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


# category-view
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


# subcategory-view
class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Subcategory.objects.all()
        category_id = self.request.query_params.get("category")

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset


# product-view
class AddProductAPIView(generics.ListCreateAPIView):
    parser_class = [MultiPartParser, FormParser]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwnerOrReadonly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'subcategory__name']

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

    # def get_queryset(self):
    #     queryset = Product.objects.all()
    #     return queryset

# product-detail
class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    parser_class = [MultiPartParser, FormParser]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

# product-rating
class ProductRatingAPIView(generics.ListCreateAPIView):
    serializer_class = ProductRatingSerializer
    queryset = Rating.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

    # def get_queryset(self):
    #     user = self.request.user
    #     return user.ratings.all()

# product-rating-detail
class ProductRatingDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductRatingSerializer
    queryset = Rating.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)


# cart-view
class CartView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.cart_items.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity')
            user = request.user

            cart_item, created = CartItem.objects.get_or_create(user=user, product_id=product_id, quantity=quantity)
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            serializer = CartItemSerializer(cart_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# cart_item-view
class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        product_id = self.kwargs['product_id']
        cart_item = CartItem.objects.filter(user=user, product_id=product_id).first()
        if not cart_item:
            return CartItem(user=user, product_id=product_id, quantity=0)
        return cart_item


# clear-cart
class ClearCartView(views.APIView):
    queryset = CartItem.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        cart_items = user.cart_items.all()
        cart_items.delete()
        return Response({"detail": "Removed all items from the cart"}, status=status.HTTP_204_NO_CONTENT)


# checkout
class OrderCheckoutView(generics.GenericAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        address = None
        address_id = request.data.get('address_id')

        shipping_method = None
        shipping_method_id = request.data.get('shipping_method')

        # address
        if address_id:
            try:
                address = Address.objects.get(pk=address_id, user=user)
                print(address)
            except Address.DoesNotExist:
                return Response({"error": "Address not found or does not belong to user"},
                                status=status.HTTP_400_BAD_REQUEST)

        if not address:
            try:
                default_address = user.profiles.address
                if default_address:
                    address = default_address
                    print(address)
                else:
                    return Response({"error": "No address provided and no address found!!!"})
            except Profile.DoesNotExist:
                return Response({"error": "User Profile not found!"}, status=status.HTTP_400_BAD_REQUEST)

        # shipping_method
        if shipping_method_id:
            try:
                shipping_method = ShippingMethod.objects.get(pk=shipping_method)
            except ShippingMethod.DoesNotExist:
                return Response({"error": "Shipping method for order not available."},
                                status=status.HTTP_400_BAD_REQUEST)

        if not cart_items.exists():
            return Response({"error": "No items in cart"}, status=status.HTTP_400_BAD_REQUEST)

        # coupon_code
        coupon_code = request.data.get('coupon_code')
        coupon = None
        discount_amount = Decimal("0.00")

        if coupon_code:
            try:
                coupon = Coupon.objects.get(coupon_code=coupon_code)
                discount_amount = coupon.discount_value
            except Coupon.DoesNotExist:
                return JsonResponse({"error": "Invalid coupon code."}, status=400)
            except Exception as e:
                return JsonResponse({"error": f"Error validating coupon: {e}"}, status=400)

        line_items = []
        total_price = Decimal("0.00")

        for item in cart_items:
            price = Decimal(item.product.price)
            discounted_price = price
            print(price)
            if discount_amount > 0:
                if coupon.discount_type == 'percentage':
                    discounted_price = price - (price * discount_amount)
                    print(discounted_price)
                elif coupon.discount_type == 'fixed':
                    discounted_price = price - discount_amount
                    print(discounted_price)
                else:
                    print("Invalid Choice")

                if discounted_price < 0:
                    discounted_price = Decimal("0.00")
            unit_amount = int(discounted_price * 100)

            line_items.append({
                "price_data": {
                    "currency": "inr",
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": item.product.name,
                        # "images": [request.build_absolute_uri(item.product.image.url)] if item.product.image else [],
                    }
                },
                "quantity": item.quantity,
            })
            # total_price += item.product.price * item.quantity #incorrect for discounted one
            total_price += discounted_price * item.quantity
            print({"total_price": total_price})
        total_price = total_price.quantize(Decimal("0.00"), ROUND_HALF_UP)
        print({"total_price": total_price})

        if total_price < 0:
            total_price = Decimal("0.00")

        order = Order.objects.create(user=user, total_price=total_price, status=Order.CHECKOUT, coupon=coupon,
                                     address=address)

        for item in cart_items:
            price = Decimal(item.product.price)
            discount_price = price
            if discount_amount > 0:
                if coupon.discount_type == 'percentage':
                    discount_price = price - (price * discount_amount)
                    print(discount_price)
                elif coupon.discount_type == 'fixed':
                    discount_price = price - discount_amount
                    print(discount_price)
                else:
                    print("Invalid Choice")
                discount_price = discount_price.quantize(Decimal("0.00"), ROUND_HALF_UP)
                print(discount_price)
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=discount_price)
        cart_items.delete()

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card", ],
                line_items=line_items,
                # invoice_creation={
                #     "enabled": True
                # },
                mode="payment",
                currency="inr",
                # success_url=request.build_absolute_uri(reverse("products:payment_success")) + f"?session_id={checkout_session['id']}",
                success_url=request.build_absolute_uri(
                    reverse("products:payment_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("products:payment_cancel")),
                metadata={"order_id": order.id, "coupon_code": coupon_code},
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.stripe_session_id = checkout_session["id"]
        order.save()

        return Response({"checkout_url": checkout_session.url}, status=status.HTTP_201_CREATED)


class PaymentSuccessView(generics.UpdateAPIView,):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        session_id = request.GET.get('session_id')

        if not session_id:
            return Response({"error": "Session ID missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            order_id = checkout_session.metadata.get('order_id')
            payment_status = checkout_session.payment_status
            payment_intent_id = checkout_session.payment_intent

            if payment_status == 'paid':
                try:
                    order = self.queryset.get(pk=order_id)
                    order.payment_status = 'completed'
                    order.payment_intent_id = payment_intent_id
                    order.status = Order.CHECKOUT

                    serializer = self.get_serializer(order, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                except Order.DoesNotExist:
                    return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"payment_status": payment_status},
                                status=status.HTTP_202_ACCEPTED)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentConfirmationView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        session_id = request.data.get('session_id')  # Get session ID from request

        if not session_id:
            return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                order_id = session.metadata.get('order_id')
                if not order_id:
                    return Response({"error": "Order ID is missing"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    order = Order.objects.get(pk=order_id)
                except Order.DoesNotExist:
                    return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

                order.payment_status = 'completed'
                order.status = Order.SHIPPED
                # to generate-tracking-number
                order.tracking_number = generate_tracking_number()
                order.save()

                return Response({"message": "Payment confirmed and order updated"}, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Payment not successful"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            print(f"Stripe Error: {e}")
            return Response({"error": f"Stripe error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(f"Error retrieving session: {e}")
            return Response({"error": f"Error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# order-history
class OrderHistioryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        user = self.request.user

        queryset = Order.objects.filter(user=user).order_by('-created_at')

        order_status = self.request.query_params.get("status")

        if order_status:
            queryset = queryset.filter(status=order_status)
        return queryset


# order-detail and cancel
class OrderDetailView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        order = self.get_object()

        if 'status' in request.data and request.data['status'] == order.CANCELLED:
            if order.status in [Order.SHIPPED, Order.DELIVERED, Order.CANCELLED]:
                return Response({'details': "You cannot cancel the order once it shipped"},
                                status=status.HTTP_400_BAD_REQUEST)

            if order.payment_intent_id:
                try:
                    payment_intent = stripe.PaymentIntent.retrieve(order.payment_intent_id)

                    if payment_intent.status == 'succeeded':
                        payment_refund = stripe.Refund.create(payment_intent=order.payment_intent_id)

                        if payment_refund.status == 'succeeded':
                            order.status = Order.CANCELLED
                            order.save()
                            return Response({'detail': "Order has been Cancelled"},
                                            status=status.HTTP_206_PARTIAL_CONTENT)
                        else:
                            return Response({'detail': "Refund failed"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'detail': "Payment was not successfull, cannot refund!!!"},
                                        status=status.HTTP_400_BAD_REQUEST)
                except  stripe.error.StripeError as e:
                    return Response({'details': f"Stripe error: {str(e)}"},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'details': "No payment information found for this order."},
                                status=status.HTTP_400_BAD_REQUEST)

        return super().patch(request, *args, **kwargs)


class CheckoutPage(TemplateView):
    template_name = 'products/checkout.html'


@csrf_exempt
def payment_cancel(request):
    return render(request, "products/payment_cancel.html")


class WishlistAPIView(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    queryset = Wishlist.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)


class CouponAPIView(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class AddressAPIView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    queryset = Address.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        return serializer.save(user=user)


class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    queryset = Address.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
