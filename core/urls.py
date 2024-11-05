


from django.urls import path
from .views import InitiatePaymentView,FlutterwaveCallbackView

from .views import RegisterView, LoginView, PropertyListCreateView, RoomListCreateView, PaymentCreateView, InvoiceDetailView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('properties/', PropertyListCreateView.as_view(), name='property-list-create'),
    path('rooms/', RoomListCreateView.as_view(), name='room-list-create'),
    path('payments/', PaymentCreateView.as_view(), name='payment-create'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('payments/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('flutterwave-callback/', FlutterwaveCallbackView.as_view(), name='flutterwave-callback'),



]

