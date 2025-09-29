from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import ParkingLot

class ParkingLotSerializer(GeoFeatureModelSerializer):
    id = serializers.IntegerField()  # Explicitly include ID
    arrived = serializers.SerializerMethodField()  # ✅ New field

    class Meta:
        model = ParkingLot
        geo_field = 'geom'
        fields = '__all__'  # This will now include 'arrived' too

    def get_arrived(self, obj):
        current_slot_id = self.context.get('current_booking_slot_id')
        current_arrived = self.context.get('current_booking_arrived', False)
        return obj.id == current_slot_id and current_arrived
