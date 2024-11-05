
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Rental Management API",
        default_version="v1",
        description="API for a rental management system",
        contact=openapi.Contact(email="contact@rentalsystem.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    # authentication_classes=('rest_framework_jwt.authentication.JSONWebTokenAuthentication',),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),  # Include our app's URL configuration
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]