import os
from django.utils.text import slugify


def get_product_image(instance, filename):
    sub_category_slug = slugify(instance.subcategory.name)
    product_slug = slugify(instance.name)
    extension = filename.split('.')[-1]
    filename = f"{sub_category_slug}_{product_slug}.{extension}"
    return os.path.join('product_images', filename)