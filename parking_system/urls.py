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
from parking.views import ParkingLotViewSet
from django.views.generic import RedirectView


router = DefaultRouter()
router.register(r'api/parkinglots', ParkingLotViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='map', permanent=False)),  # 👈 redirect root to /map/
    path('', include(router.urls)),
    path('', include('parking.urls')),  # this includes the URLs from the parking app


    
   

   

]
