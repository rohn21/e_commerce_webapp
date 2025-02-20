import os
from django.utils.text import slugify
import time
import random
import string

# products-image-path
def get_product_image(instance, filename):
    sub_category_slug = slugify(instance.subcategory.name)
    product_slug = slugify(instance.name)
    extension = filename.split('.')[-1]
    filename = f"{sub_category_slug}_{product_slug}.{extension}"
    return os.path.join('product_images', filename)

# tracking_number
def generate_tracking_number():
    timestamp = str(int(time.time()))
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ID-{timestamp}-{random_chars}"