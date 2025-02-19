from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics, views, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from accounts.permissions import IsOwnerOrReadonly
from products.models import (Category, Subcategory,
                             Product, CartItem, Rating,
                             OrderItem, Order, Wishlist,
                             Coupon)
from products.serializers import (CategorySerializer, SubCategorySerializer,
                                  ProductSerializer, ProductRatingSerializer,
                                  CartItemSerializer,
                                  OrderSerializer, OrderItemSerializer,
                                  WishlistSerializer, CouponSerializer)
from products.filters import ProductFilter
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from decimal import Decimal, ROUND_HALF_UP
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


# Create your views here.

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


class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    parser_class = [MultiPartParser, FormParser]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


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

        if not cart_items.exists():
            return Response({"error": "No items in cart"}, status=status.HTTP_400_BAD_REQUEST)

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

        stripe.api_key = settings.STRIPE_SECRET_KEY

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
            # total_price += item.product.price * item.quantity
            total_price += discounted_price * item.quantity
            print({"total_price": total_price})
        total_price = total_price.quantize(Decimal("0.00"), ROUND_HALF_UP)
        print({"total_price": total_price})

        if total_price < 0:  # Prevent negative total_price
            total_price = Decimal("0.00")

        order = Order.objects.create(user=user, total_price=total_price, status=Order.CHECKOUT, coupon=coupon)

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

class PaymentSuccessView(generics.UpdateAPIView):
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

            if payment_status == 'paid':
                try:
                    order = self.queryset.get(pk=order_id)
                    order.payment_status = 'completed'
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

# class PaymentConfirmationView(APIView):


# class CreateCheckoutSession(APIView):
#         def post(self, request):
#             dataDict = dict(request.data)
#             price = dataDict['price'][0]
#             product_name = dataDict['product_name'][0]
#             try:
#                 checkout_session = stripe.checkout.Session.create(
#                     line_items=[{
#                         'price_data': {
#                             'currency': 'usd',
#                             'product_data': {
#                                 'name': product_name,
#                             },
#                             'unit_amount': price
#                         },
#                         'quantity': 1
#                     }],
#                     mode='payment',
#                     success_url=FRONTEND_CHECKOUT_SUCCESS_URL,
#                     cancel_url=FRONTEND_CHECKOUT_FAILED_URL,
#                 )
#                 return redirect(checkout_session.url, code=303)
#             except Exception as e:
#                 print(e)
#                 return e

# order-history
class OrderHistioryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.filter(user=user).order_by('-created_at')
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

            order.status = Order.CANCELLED
            order.save()
            return Response({'detail': "Order has been Cancelled"}, status=status.HTTP_206_PARTIAL_CONTENT)

        return super().patch(request, *args, **kwargs)


class CheckoutPage(TemplateView):
    template_name = 'products/checkout.html'


# @csrf_exempt
# def payment_success(request):
#     session_id = request.GET.get('session_id')
#
#     if not session_id:
#         return JsonResponse({"error": "Session ID missing"}, status=400)
#
#     try:
#         checkout_session = stripe.checkout.Session.retrieve(session_id)
#
#         # can also retrieve more details like payment status, customer info, etc.
#         order_id = checkout_session.metadata.get('order_id')
#         payment_status = checkout_session.payment_status
#
#         # Process the order and confirm payment success
#         if payment_status == 'paid':
#
#             pass
#
#         return render(request, "products/payment_success.html", {"order_id": order_id, "payment_status": payment_status})
#     except stripe.error.StripeError as e:
#         return JsonResponse({"error": str(e)}, status=400)

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
