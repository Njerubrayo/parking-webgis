from django.db import models
from django.contrib.gis.db import models
from django.contrib.auth.models import User

class ParkingLot(models.Model):
     id = models.AutoField(primary_key=True)
     slot_no = models.CharField(max_length=100, db_column='Slot_No')
     status = models.CharField(max_length=50, null=True, blank=True, db_column='Status')
     vehicle = models.CharField(max_length=100, null=True, blank=True, db_column='Vehicle')
     lot_id = models.CharField(max_length=300, db_column= 'Lot_ID')
     road_name = models.CharField(max_length=255, db_column='Road_Name')
     lot_type = models.CharField(max_length=50, null=True, blank=True, db_column='Lot_type')
     geom = models.MultiPolygonField(srid=4326, db_column='geom')  # Adjust if different

     class Meta:
        managed = False  # ⚠️ prevents Django from modifying the table and Because table was created outside Django
        db_table = 'parking_lots'   # exact table name in PostgreSQL

     def __str__(self):
        return f"{self.slot_no} - {self.road_name}"
     

    

from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.OneToOneField(ParkingLot, on_delete=models.CASCADE)  # one booking per slot
    vehicle_reg = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    booked_at = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField()  # 💡 in minutes

    def is_expired(self):
        
        expiry_time = self.booked_at + timedelta(minutes=self.duration_minutes)
        return timezone.now() > expiry_time

    def __str__(self):
        return f"Booking for {self.slot.slot_no} by {self.user.username}"
