from django.contrib import admin
from .models import ParkingLot, Booking, BookingEvent, UserProfile

@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('slot_no', 'road_name', 'lot_id', 'status', 'vehicle')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'vehicle_type', 'vehicle_reg', 'status', 'booked_at')

@admin.register(BookingEvent)
class BookingEventAdmin(admin.ModelAdmin):
    list_display = ('booking', 'event_type', 'timestamp')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
