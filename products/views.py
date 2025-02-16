from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
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
                             OrderItem, Order,
                             Wishlist)
from products.serializers import (CategorySerializer, SubCategorySerializer,
                                  ProductSerializer, ProductRatingSerializer,
                                  CartItemSerializer,
                                  OrderSerializer, OrderItemSerializer,
                                  WishlistSerializer)
from products.filters import ProductFilter
from django.conf import settings
from django.views.generic import TemplateView
import stripe


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
# class OrderCheckoutView(generics.GenericAPIView):
#     serializer_class = OrderSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def post(self, request, *args, **kwargs):
#         user = request.user
#         cart_items = CartItem.objects.filter(user=user)

#         if not cart_items.exists():
#             return Response({'detail': 'No items in cart'}, status=status.HTTP_400_BAD_REQUEST)

#         total_price = sum(item.product.price * item.quantity for item in cart_items)

#         order = Order.objects.create(user=user, total_price=total_price, status=Order.CHECKOUT)
        
#         line_items = []

#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.price
#             )
#             line_items.append({
#                 'price_data': {
#                     'currency': 'inr',  # INR for India-based payments
#                     'product_data': {'name': item.product.name},  # Use actual product name
#                     'unit_amount': int(item.product.price * 100),  # Convert to paisa
#                 },
#                 'quantity': item.quantity,  # Use actual quantity from cart
#             })

#         cart_items.delete()  # empty cart once checkout
#         key = settings.STRIPE_SECRET_KEY
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#         print(key)
        
#         try:
#             # Create Stripe Checkout Session
#             session = stripe.checkout.Session.create(
#                 payment_method_types=['card'],
#                 line_items=line_items,  # Actual cart items
#                 mode='payment',
#                 success_url=request.build_absolute_uri('/payment-success/'),
#                 cancel_url=request.build_absolute_uri('/checkout-failed/'),
#                 metadata={'order_id': order.id}
#                 # line_items=[
#                 #     {
#                 #         'price_data': {
#                 #             'currency': 'inr',
#                 #             'product_data': {'name': 'Your Order'},
#                 #             'unit_amount': int(total_price * 100),  # Convert to paisa
#                 #         },
#                 #         'quantity': 1,
#                 #     }
#                 # ],
#                 # mode='payment',
#                 # success_url=request.build_absolute_uri('/payment-success/'),
#                 # cancel_url=request.build_absolute_uri('/checkout-failed/'),
#                 # metadata={'order_id': order.id}
#             )

#             order.payment_intent_id = session.id
#             order.save()

#             return Response({"checkout_url": session.url}, status=status.HTTP_201_CREATED) 
        
#         except stripe.error.StripeError as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         except Exception as e:
#             return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
        
class OrderCheckoutView(generics.GenericAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        if not cart_items.exists():
            return Response({"error": "No items in cart"}, status=status.HTTP_400_BAD_REQUEST)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        line_items = []
        total_price = 0

        for item in cart_items:
            line_items.append({
                "price_data": {
                    "currency":"inr",
                    "unit_amount": int(item.product.price * 100),  # INR to Paisa
                    "product_data": {
                        "name": item.product.name
                    }
                },
                "quantity": item.quantity,
            })
            total_price += item.product.price * item.quantity

        # Create an Order
        order = Order.objects.create(user=user, total_price=total_price, status=Order.CHECKOUT)

        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)

        cart_items.delete()  # Empty the cart after checkout

        # Create Stripe Checkout Session for INR Payments
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card",],  # Only INR payment methods
                line_items=line_items,
                mode="payment",
                currency="inr",
                success_url=request.build_absolute_uri(reverse("products:payment_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("products:payment_cancel")),
                metadata={"order_id": order.id},
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.payment_intent_id = checkout_session["id"]
        order.save()

        return Response({"checkout_url": checkout_session.url}, status=status.HTTP_201_CREATED) 
    
class StripeWebhookView(APIView):
    """Handles Stripe Webhook Events"""
    permission_classes = [AllowAny]  # Webhooks don't require authentication

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET  # Store in settings.py

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return JsonResponse({"error": "Invalid payload"}, status=400)
        except stripe.error.SignatureVerificationError:
            return JsonResponse({"error": "Invalid signature"}, status=400)

        # Handle Payment Success Event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")

            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    order.status = "PAID" 
                    order.save()
                except Order.DoesNotExist:
                    return JsonResponse({"error": "Order not found"}, status=404)

        return JsonResponse({"status": "success"}, status=200)

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
def checkout_page(request):
    return render(request, "products/checkout.html", {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLISHABLE_KEY
    })

@csrf_exempt
def payment_success(request):
    return render(request, "products/payment_success.html")


@csrf_exempt
def payment_cancel(request):
    return render(request, "products/payment_cancel.html")

class PaymentConfirmationView(APIView):
    def post(self, request, *args, **kwargs):
        # Receive the payment intent ID and the payment method ID from frontend
        payment_intent_id = request.data.get('payment_intent_id')
        payment_method_id = request.data.get('payment_method_id')

        if not payment_intent_id or not payment_method_id:
            return Response({'detail': 'Missing payment details'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Confirm the PaymentIntent on Stripe
            payment_intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )

            # Check if payment was successful
            if payment_intent['status'] == 'succeeded':
                # Payment was successful, update order status
                order = Order.objects.get(payment_intent_id=payment_intent_id)
                order.status = Order.Completed  # Update status to "Paid"
                order.save()

                return Response({'detail': 'Payment successful', 'order_id': order.id}, status=status.HTTP_200_OK)
            else:
                return Response({'detail': 'Payment failed'}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({'detail': f'Stripe error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


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


from django.utils.decorators import method_decorator

@csrf_exempt
def checkout_view(request, order_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # Call checkout API to get client_secret
    response = request.session.get("checkout_response", {})
    order = get_object_or_404(Order, id=order_id)
    
    if "client_secret" not in response:
        return render(request, "products/checkout.html", {"error": "Client secret not found. Try again."})

    return render(request, "products/checkout.html", {
        "client_secret": response["client_secret"],
        "total_price": response.get("total_price", 0),
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY
    })

class WishlistAPIView(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    queryset = Wishlist.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)
