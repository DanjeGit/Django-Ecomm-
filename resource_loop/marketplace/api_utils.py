from django.http import JsonResponse
from .models import PickupStation

def get_pickup_stations(request):
    sub_county = request.GET.get('sub_county')
    if sub_county:
        stations = PickupStation.objects.filter(sub_county=sub_county).values('id', 'name', 'address')
        return JsonResponse(list(stations), safe=False)
    return JsonResponse([], safe=False)
