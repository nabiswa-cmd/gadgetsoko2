from .models import CartItem
from django.db.models import Sum

def cart_count(request):
    count = 0

    if request.user.is_authenticated:
        result = CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )
        count = result['total'] or 0

    return {'cart_count': count}

from .models import Order

def active_orders(request):
    if request.user.is_authenticated:
        count = Order.objects.filter(
            user=request.user
        ).exclude(status__in=['Delivered', 'Cancelled']).count()
        return {'active_order_count': count}
    return {'active_order_count': 0}


from django.conf import settings

def google_settings(request):
    return {
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID
    }