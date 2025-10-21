from django.urls import path
from .views import map_view, register_view, login_view, logout_view, book_slot_view, reservation_over_view, cancel_booking_view, extend_booking_view, mark_arrived, booking_status_view, active_parking_list, no_show_parking_list, add_staff, admin_dashboard_data


urlpatterns = [
    path('map/', map_view, name='map'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('book/<int:slot_id>/', book_slot_view, name='book_slot'),
    path('reservation-over/', reservation_over_view, name='reservation_over'),
    path('cancel-booking/', cancel_booking_view, name='cancel_booking'),
    path('extend-booking/', extend_booking_view, name='extend_booking'),
    path('mark-arrived/', mark_arrived, name='mark_arrived'),
    path('booking-status/', booking_status_view, name='booking_status'),
    path('api/bookings/active/', active_parking_list, name='active_parking_list'),
    path('api/bookings/no_show/', no_show_parking_list, name='no_show_parking_list'),
    path('api/staff/add/', add_staff, name='add_staff'),
    path('api/admin/dashboard-data/', admin_dashboard_data, name='admin_dashboard_data'),


]




