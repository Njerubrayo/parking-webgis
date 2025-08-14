from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import ParkingLot, Booking
from .serializers import ParkingLotSerializer
from django.middleware.csrf import get_token



from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class ParkingLotViewSet(viewsets.ModelViewSet):  # Not ReadOnlyModelViewSet
    queryset = ParkingLot.objects.all()
    serializer_class = ParkingLotSerializer

  


from django.contrib.auth.decorators import login_required
@login_required(login_url='/login/')

def map_view(request):
    auto_release_expired_bookings()
    current_booking = Booking.objects.filter(user=request.user).first()



    return render(request, 'map.html', { 
          'current_booking_id': current_booking.slot.id if current_booking else None,


          'csrf_token': get_token(request)  # To allow dynamic use in JS
    })



from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegistrationForm
from django.contrib.auth.models import User

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 == password2:
            # Check if username or email already exists (optional but good)
            if User.objects.filter(username=username).exists():
                return render(request, 'register.html', {'error': 'Username already exists'})
            if User.objects.filter(email=email).exists():
                return render(request, 'register.html', {'error': 'Email already registered'})

            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)  # Auto-login after registration
            return redirect('/map/')  # ✅ Redirect to map after successful registration
        else:
            return render(request, 'register.html', {'error': 'Passwords do not match'})

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
       
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)  # adapt if you use custom auth
        if user is not None:
            login(request, user)
            return redirect('/map/')
       


        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "login.html")


from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    response = redirect('/login/')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
@login_required
def book_slot_view(request, slot_id):
    user = request.user

    # Check if user has active booking
    active_booking = Booking.objects.filter(user=user).first()
    if active_booking and not active_booking.is_expired():
        return render(request, 'booking_form.html', {
            'error': 'Driver has already reserved a lot.',
            'slot_no': active_booking.slot.slot_no,
            'slot_id': active_booking.slot.id
           
        })

    # Load slot
    slot = ParkingLot.objects.get(id=slot_id)


    if request.method == 'POST':
        vehicle = request.POST.get('vehicle')
        phone = request.POST.get('phone')
        time_minutes = int(request.POST.get('book_time'))

        Booking.objects.create(
            user=user,
            slot=slot,
            vehicle_reg=vehicle,
            phone_number=phone,
            duration_minutes=time_minutes
        )

        slot.status = "occupied"
        slot.save()
        return redirect('/map/')  # redirect back to map

    return render(request, 'booking_form.html', {
        'slot_no': slot.slot_no,
       'slot_id': slot_id
    })


 

def auto_release_expired_bookings():
    now = timezone.now()
    expired_bookings = Booking.objects.all()

    for booking in expired_bookings:
        expiry_time = booking.booked_at + timedelta(minutes=booking.duration_minutes)
        if now > expiry_time:
            booking.slot.status = 'available'
            booking.slot.save()
            booking.delete()
