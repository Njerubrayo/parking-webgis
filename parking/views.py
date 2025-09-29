from django.shortcuts import render, redirect
from rest_framework import viewsets
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import never_cache
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance, Transform
import json
from .models import ParkingLot, Booking, UserProfile
from .serializers import ParkingLotSerializer
from django.db.models import Count, Sum
from django.db.models.functions import ExtractWeekDay

GRACE_PERIOD_MINUTES = 10
MAX_EXTENSION_SECONDS = 6 * 60 * 60  # optional safety cap
class ParkingLotViewSet(ReadOnlyModelViewSet):
    queryset = ParkingLot.objects.all()
    serializer_class = ParkingLotSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 300)

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.annotate(
                    distance=Distance(Transform('geom', 3857), Transform(user_location, 3857))
                ).filter(distance__lte=float(radius))
            except (ValueError, TypeError):
                pass

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        current_booking = None
        if self.request.user.is_authenticated:
            current_booking = Booking.objects.filter(
                user=self.request.user,
                status__in=['active', 'arrived']
            ).select_related('slot').first()

        context['current_booking_slot_id'] = current_booking.slot.id if current_booking else None
        context['current_booking_arrived'] = bool(current_booking and current_booking.status == 'arrived')
        return context

@login_required(login_url='/login/')
@never_cache
def map_view(request):
    # Always run expiry/no_show cleanup
    auto_release_expired_bookings()

    # Detect role safely
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'user'

    current_booking = None
    expiry_ts_ms = None
    grace_ts_ms = None

    # Only fetch booking/timers for normal users
    if role == 'user':
        current_booking = Booking.objects.filter(
            user=request.user,
            status__in=['active', 'arrived']
        ).first()

        if current_booking:
            expiry_time = current_booking.booked_at + timedelta(minutes=current_booking.duration_minutes)
            expiry_ts_ms = int(expiry_time.timestamp() * 1000)

            grace_time = current_booking.booked_at + timedelta(minutes=GRACE_PERIOD_MINUTES)
            grace_ts_ms = int(grace_time.timestamp() * 1000)

    return render(request, 'map.html', {
        'current_booking_id': current_booking.slot.id if current_booking else None,
        'expiry_ts_ms': expiry_ts_ms,
        'grace_ts_ms': grace_ts_ms,
        'csrf_token': get_token(request),
        'username': request.user.username,
        'role': role,
    })

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 == password2:
            if User.objects.filter(username=username).exists():
                return render(request, 'register.html', {'error': 'Username already exists'})
            if User.objects.filter(email=email).exists():
                return render(request, 'register.html', {'error': 'Email already registered'})
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            return redirect('/map/')
        else:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/map/')
        else:
            # Add error message to be displayed in template
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    response = redirect('/login/')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
def book_slot_view(request, slot_id):
    user = request.user

    # Only block if booking is still active or arrived
    active_booking = Booking.objects.filter(
        user=user,
        status__in=['active', 'arrived']
    ).first()
    if active_booking:
        return render(request, 'booking_form.html', {
            'error': 'Driver has already reserved a lot.',
            'slot_no': active_booking.slot.slot_no,
            'slot_id': active_booking.slot.id
        })

    from django.db import transaction
    with transaction.atomic():
        slot = ParkingLot.objects.select_for_update().get(id=slot_id)

    if request.method == 'POST':
        vehicle_type = request.POST.get('vehicle_type', '').strip().upper()
        allowed_types = [t[0] for t in Booking.VEHICLE_TYPE_CHOICES]
        if vehicle_type not in allowed_types:
            return render(request, 'booking_form.html', {
                'error': 'Invalid vehicle type',
                'slot_no': slot.slot_no,
                'slot_id': slot_id
            })

        vehicle = request.POST.get('vehicle', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Validate required fields
        if not vehicle:
            return render(request, 'booking_form.html', {
                'error': 'Vehicle registration is required',
                'slot_no': slot.slot_no,
                'slot_id': slot_id
            })
        if not phone:
            return render(request, 'booking_form.html', {
                'error': 'Phone number is required',
                'slot_no': slot.slot_no,
                'slot_id': slot_id
            })

        # Safely parse time inputs, defaulting to 0 if blank/invalid
        try:
            hours = int(request.POST.get('hours') or 0)
        except ValueError:
            hours = 0
        try:
            minutes = int(request.POST.get('minutes') or 0)
        except ValueError:
            minutes = 0
        try:
            seconds = int(request.POST.get('seconds') or 0)
        except ValueError:
            seconds = 0

        # Clamp minutes/seconds to valid ranges
        minutes = max(0, min(59, minutes))
        seconds = max(0, min(59, seconds))
        hours = max(0, hours)

        time_minutes = hours * 60 + minutes + (seconds / 60)

        # Require non-zero booking time
        if time_minutes <= 0:
            return render(request, 'booking_form.html', {
                'error': 'Reservation time is required',
                'slot_no': slot.slot_no,
                'slot_id': slot_id
            })

        Booking.objects.create(
            user=user,
            slot=slot,
            vehicle_type=vehicle_type,
            vehicle_reg=vehicle,
            phone_number=phone,
            duration_minutes=time_minutes,
            status='active'
        )

        slot.status = "occupied"
        slot.save()
        return redirect('/map/')

    return render(request, 'booking_form.html', {
        'slot_no': slot.slot_no,
        'slot_id': slot_id
    })



def auto_release_expired_bookings():
    now = timezone.now()
    candidates = Booking.objects.filter(status__in=['active', 'arrived'])

    for booking in candidates.select_related('slot'):
        expiry_time = booking.booked_at + timedelta(minutes=booking.duration_minutes)
        grace_time = booking.booked_at + timedelta(minutes=GRACE_PERIOD_MINUTES)

        if booking.arrived_at:
            # Driver arrived — check if time is over
            if now > expiry_time:
                booking.status = 'expired'
                booking.slot.status = 'available'
                booking.slot.save(update_fields=['status'])
                booking.save(update_fields=['status'])
                log_booking_event(booking, 'expired', 'Reservation time ended')
        else:
            # Driver never arrived — check grace period
            if now > grace_time:
                booking.status = 'no_show'
                booking.slot.status = 'available'
                booking.slot.save(update_fields=['status'])
                booking.save(update_fields=['status'])
                log_booking_event(booking, 'no_show', 'User did not arrive within grace period')


@login_required(login_url='/login/')
def reservation_over_view(request):
    return render(request, 'reservation_over.html')

@login_required
def cancel_booking_view(request):
   booking = Booking.objects.filter(
    user=request.user,
    status__in=['active', 'arrived']
).first()
   if booking:
    booking.status = 'cancelled'
    booking.slot.status = 'available'
    booking.slot.save()
    booking.save()
    return redirect('/map/')

@login_required
def extend_booking_view(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    booking = Booking.objects.filter(
        user=request.user,
        status__in=['active', 'arrived']  # allow extension after arrival
    ).first()
    if not booking:
        return JsonResponse({'error': 'No active booking'}, status=400)
    try:
        data = json.loads(request.body.decode('utf-8'))
        hours = int(data.get('hours') or 0)
        minutes = int(data.get('minutes') or 0)
        seconds = int(data.get('seconds') or 0)
    except Exception:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    extra_minutes = hours * 60 + minutes + (seconds / 60)
    if extra_minutes <= 0:
        return JsonResponse({'error': 'Nothing to extend'}, status=400)
    booking.duration_minutes = float(booking.duration_minutes) + float(extra_minutes)
    booking.save(update_fields=['duration_minutes'])
    expiry_time = booking.booked_at + timedelta(minutes=booking.duration_minutes)
    expiry_ts_ms = int(expiry_time.timestamp() * 1000)
    return JsonResponse({'ok': True, 'expiry_ts_ms': expiry_ts_ms})



@login_required
@require_POST
def mark_arrived(request):
    try:
        payload = json.loads(request.body or '{}')
        booking_id = payload.get('booking_id')
        if not booking_id:
            return JsonResponse({'ok': False, 'error': 'Missing booking_id'}, status=400)

        booking = Booking.objects.select_related('slot').get(
            slot__id=booking_id,  # using slot id since that's what frontend sends
            user=request.user,
            status='active'
        )

        if booking.arrived_at:
            return JsonResponse({
                'ok': True,
                'already_arrived': True,
                'arrived_at': booking.arrived_at.isoformat(),
                'status': booking.status
            })

        booking.arrived_at = timezone.now()
        booking.status = 'arrived'   # ✅ set new status
        booking.save(update_fields=['arrived_at', 'status'])

        if booking.slot.status != 'occupied':
            booking.slot.status = 'occupied'
            booking.slot.save(update_fields=['status'])

        return JsonResponse({
            'ok': True,
            'arrived_at': booking.arrived_at.isoformat(),
            'status': booking.status
        })
    except Booking.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Booking not found or not yours'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def log_booking_event(booking, event_type, notes=''):
    from .models import BookingEvent
    BookingEvent.objects.create(
        booking=booking,
        event_type=event_type,
        notes=notes
    )




@login_required
@require_GET
def booking_status_view(request):
    # Keep your server state fresh
    auto_release_expired_bookings()

    booking = Booking.objects.filter(user=request.user).order_by('-booked_at').first()
    if not booking:
        return JsonResponse({'has_booking': False})

    expiry_ts_ms = int((booking.booked_at + timedelta(minutes=booking.duration_minutes)).timestamp() * 1000)
    from_time = booking.booked_at
    GRACE_PERIOD_MINUTES = 10  # keep in sync with your constant in map_view
    grace_ts_ms = int((from_time + timedelta(minutes=GRACE_PERIOD_MINUTES)).timestamp() * 1000)

    return JsonResponse({
        'has_booking': True,
        'status': booking.status,           # active | arrived | expired | cancelled | no_show
        'arrived_at': booking.arrived_at.isoformat() if booking.arrived_at else None,
        'expiry_ts_ms': expiry_ts_ms,
        'grace_ts_ms': grace_ts_ms,
        'slot_id': booking.slot.id
    })


def is_staff_or_admin(user):
    try:
        return user.profile.role in ['staff', 'admin']
    except UserProfile.DoesNotExist:
        return False

@login_required
def active_parking_list(request):
    if not is_staff_or_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    bookings = Booking.objects.filter(status__in=['active', 'arrived']).select_related('slot', 'user')
    data = [{
        'id': b.id,
        'username': b.user.username,
        'slot_no': b.slot.slot_no,
        'road_name': b.slot.road_name,
        'status': b.status,
        'vehicle_type': b.vehicle_type,
        'booked_at': b.booked_at.isoformat(),
    } for b in bookings]
    return JsonResponse({'bookings': data})


@login_required
def no_show_parking_list(request):
    if not is_staff_or_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    bookings = Booking.objects.filter(status='no_show').select_related('slot', 'user')
    data = [{
        'id': b.id,
        'username': b.user.username,
        'slot_no': b.slot.slot_no,
        'road_name': b.slot.road_name,
        'status': b.status,
        'vehicle_type': b.vehicle_type,
        'booked_at': b.booked_at.isoformat(),
    } for b in bookings]
    return JsonResponse({'bookings': data})


@login_required
@require_POST
def add_staff(request):
    if request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Forbidden'}, status=403)

    data = json.loads(request.body)
    username = data.get('username')
    password = data.get('password', 'pass123')

    if not username:
        return JsonResponse({'error': 'Username required'}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'User already exists'}, status=400)

    # Create the Django user
    user = User.objects.create_user(username=username, password=password)
    user.is_staff = False  # Optional: Django admin access
    user.save()

    # ✅ Update the existing profile instead of creating a new one
    profile = user.profile
    profile.role = 'staff'
    profile.save()

    return JsonResponse({'ok': True, 'message': f'Staff {username} created'})

@login_required
def admin_dashboard_data(request):
    # Role check
    if request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Forbidden'}, status=403)

    # ===== Summary stats =====
    # New:
    total_arrived = Booking.objects.filter(status='arrived').count()
    total_no_show = Booking.objects.filter(status='no_show').count()
    total_expired = Booking.objects.filter(status='expired').count()
    total_revenue = Booking.objects.filter(payment_status='paid') \
        .aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

    # ===== Overall vehicle counts =====
    vehicle_counts = list(
        Booking.objects.values('vehicle_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ===== Vehicle counts by day =====
    raw_daily = (
        Booking.objects
        .annotate(weekday=ExtractWeekDay('booked_at'))
        .values('weekday', 'vehicle_type')
        .annotate(count=Count('id'))
    )

    day_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday',
               5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

    # Initialize all days with empty dicts
    vehicle_counts_by_day = {day: {} for day in day_order}

    for entry in raw_daily:
        day_name = day_map.get(entry['weekday'])
        if day_name:
            vehicle_counts_by_day[day_name][entry['vehicle_type']] = entry['count']

    # ===== Revenue by day =====
    raw_revenue = (
        Booking.objects
        .filter(payment_status='paid')
        .annotate(weekday=ExtractWeekDay('booked_at'))
        .values('weekday')
        .annotate(total=Sum('amount_paid'))
    )

    revenue_by_day = {day: 0 for day in day_order}

    for entry in raw_revenue:
        day_name = day_map.get(entry['weekday'])
        if day_name:
            revenue_by_day[day_name] = float(entry['total'] or 0)

    # ===== Response =====
    return JsonResponse({
        'total_arrived': total_arrived,
        'total_no_show': total_no_show,
        'total_expired': total_expired,
        'total_revenue': total_revenue,
        'vehicle_counts': vehicle_counts,
        'vehicle_counts_by_day': vehicle_counts_by_day,
        'revenue_by_day': revenue_by_day
    })