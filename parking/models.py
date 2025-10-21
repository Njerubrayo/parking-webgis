from django.db import models
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

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

class Booking(models.Model):    
    VEHICLE_TYPE_CHOICES = [
        ('PRIVATE', 'PRIVATE'),
        ('PICKUP', 'PICKUP'),
        ('MOTORBIKE', 'MOTORBIKE'),
        ('TUKTUK', 'TUKTUK'),
        ('CANTER', 'CANTER'),
        ('TAXI', 'TAXI'),
        ('LORRY', 'LORRY'),
        ('MINIBUS', 'MINIBUS'),
        ('TRAILER', 'TRAILER'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE)
    #slot = models.OneToOneField(ParkingLot, on_delete=models.CASCADE)  # one booking per slot
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='PRIVATE')
    vehicle_reg = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    booked_at = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField()  # 💡 in minutes

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('arrived', 'Arrived'),   
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=16,
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
        default='pending'
    )
    mpesa_receipt = models.CharField(max_length=64, blank=True, default='')
    merchant_request_id = models.CharField(max_length=64, blank=True, default='')  # echo from STK
    checkout_request_id = models.CharField(max_length=64, blank=True, default='')

    def is_expired(self):
        
        expiry_time = self.booked_at + timedelta(minutes=self.duration_minutes)
        return timezone.now() > expiry_time

    def __str__(self):
        return f"Booking for {self.slot.slot_no} by {self.user.username}"



  # NEW: record when the user actually arrived (optional but recommended)
    arrived_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        expiry_time = self.booked_at + timedelta(minutes=self.duration_minutes)
        return timezone.now() > expiry_time

    def __str__(self):
        return f"Booking for {self.slot.slot_no} by {self.user.username}"

class BookingEvent(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)  # 'expired', 'no_show', etc.
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.event_type} for booking {self.booking.id} at {self.timestamp}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    from .models import UserProfile  # avoid circular import if needed
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists for older users
        UserProfile.objects.get_or_create(user=instance)
