from django.urls import path
from .views import map_view, register_view, login_view, logout_view, booking_status_view, active_parking_list, no_show_parking_list, add_staff, admin_dashboard_data


urlpatterns = [
    path('map/', map_view, name='map'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('booking-status/', booking_status_view, name='booking_status'),
    path('api/bookings/active/', active_parking_list, name='active_parking_list'),
    path('api/bookings/no_show/', no_show_parking_list, name='no_show_parking_list'),
    path('api/staff/add/', add_staff, name='add_staff'),
    path('api/admin/dashboard-data/', admin_dashboard_data, name='admin_dashboard_data'),


]




