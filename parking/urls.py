from django.urls import path
from .views import map_view, register_view, login_view, logout_view
from . import views

urlpatterns = [
    path('map/', map_view, name='map'),
   
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('map/', views.map_view, name='map'),
    path('logout/', views.logout_view, name='logout'),
    #path('book/<int:slot_id>/', views.book_slot_view, name='book_slot'),

]

#from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ParkingLotViewSet

from rest_framework.decorators import action
from rest_framework.response import Response

# For the custom action, define a route manually
#parkinglot_update = ParkingLotViewSet.as_view({
 #   'patch': 'update_status',
#})

urlpatterns = [
    path('map/', map_view, name='map'),
   
]
