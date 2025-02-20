from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Avg
from products.models import (Category, Subcategory,
                             Product, Rating, CartItem,
                             OrderItem, Order, Wishlist,
                             Coupon, Address)

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']
        # depth = 1


class SubCategorySerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Subcategory
        fields = ['id', 'category', 'name', 'description']


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.all())

    # image = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)

    class Meta:
        model = Product
        fields = ['id', 'category', 'subcategory', 'name', 'description', 'price', 'available_quantity', 'image']

    # unique product_name
    def validate_name(self, value):
        queryset = Product.objects.filter(name=value).exists()
        if queryset:
            raise serializers.ValidationError("Product with this name already exists.")
        return value

    # def create(self, validated_data):
    #     images = validated_data.pop('image', [])
    #     print(images)# Get the list of images
    #     product = Product.objects.create(**validated_data)
    #
    #     # Save the first image to the default image field (if any)
    #     if images:
    #         product.image = images[0]
    #         product.save()
    #
    #     return product
    #
    # def update(self, instance, validated_data):
    #     images = validated_data.pop('image', []) if 'image' in validated_data else []
    #
    #     # Update other fields
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
    #
    #     # Update the default image (if any)
    #     if images:
    #         instance.image = images[0]  # Update the first image
    #         instance.save()
    #
    #     return instance


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'product', 'rating', 'comment']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, required=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']

    def validate_quantity(self, attrs):
        if attrs <= 0:
            raise serializers.ValidationError("Product quantity must be positive.!!!")
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'total_price', 'status', 'order_items']


class WishlistSerializer(serializers.ModelSerializer):
    product_review = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_review']

    def get_product_review(self, obj):
        ratings = obj.product.ratings.all()
        if ratings.exists():
            return ratings.aggregate(average_rating=Avg('rating'))['average_rating']
        return None


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'coupon_code', 'discount_value', 'max_discount', 'expires_at', 'is_active', 'discount_type', 'usage', 'created_at']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'city', 'street', 'state', 'pincode', 'is_default']

    def validate_pincode(self, attrs):
        pincode = str(attrs)
        if len(pincode) != 6:
            raise serializers.ValidationError("Pincode must be 6 digits!!!")

        if not pincode.isdigit():
            raise serializers.ValidationError("Pincode must contains only digits.")
        return attrs
