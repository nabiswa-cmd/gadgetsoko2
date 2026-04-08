from django.contrib.sitemaps import Sitemap
from app.models import Product  # Import your Product model

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()  # Include all products

    def lastmod(self, obj):
        return obj.updated_at  # Assumes you have an 'updated_at' field
    
