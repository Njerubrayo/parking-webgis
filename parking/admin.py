
from django.contrib import admin
from .models import ParkingLot

@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('slot_no', 'road_name', 'lot_id', 'status', 'vehicle')
