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