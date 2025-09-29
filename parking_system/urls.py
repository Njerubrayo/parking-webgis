"""
URL configuration for parking_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from parking.views import ParkingLotViewSet, map_view, register_view, login_view, logout_view, book_slot_view, reservation_over_view, cancel_booking_view, extend_booking_view, mark_arrived

router = DefaultRouter()
router.register(r'api/parkinglots', ParkingLotViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('map/', map_view, name='map'),  # 👈 this is what you're missing
    path('', include('parking.urls')),  # this includes the URLs from the parking app
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('book/<int:slot_id>/', book_slot_view, name='book_slot'),
    path('reservation-over/', reservation_over_view, name='reservation_over'),
    path('cancel-booking/', cancel_booking_view, name='cancel_booking'),
    path('extend-booking/', extend_booking_view, name='extend_booking'),
    path('mark-arrived/', mark_arrived, name='mark_arrived'),


    
   

   

]
