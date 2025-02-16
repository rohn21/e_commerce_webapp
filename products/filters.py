from dataclasses import fields

from django_filters import rest_framework as filters
from .models import Product, CartItem

class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    min_price = filters.CharFilter(field_name='price', lookup_expr='gte')
    max_price = filters.CharFilter(field_name='price', lookup_expr='lte')


    model = Product
    fields = ['category', 'min_price', 'max_price']