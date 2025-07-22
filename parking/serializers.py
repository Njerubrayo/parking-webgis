from rest_framework import serializers

from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import ParkingLot

class ParkingLotSerializer(GeoFeatureModelSerializer):

     id = serializers.IntegerField()  # Explicitly include ID
     class Meta:
        model = ParkingLot
        geo_field = 'geom'  # Make sure this matches your geometry field
        fields = '__all__'

