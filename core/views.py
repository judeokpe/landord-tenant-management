
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework import serializers
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import Payment, Invoice
from .serializers import PaymentSerializer, InvoiceSerializer
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from .models import Property, Room
from .serializers import PropertySerializer, RoomSerializer
# core/views.py

import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Payment
from .serializers import PaymentSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": {
                "email": user.email,
                "role": user.role,
                "phone_number": user.phone_number,
            }
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = serializer.get_tokens_for_user(user)
        return Response({
            "user": {
                "email": user.email,
                "role": user.role,
                "phone_number": user.phone_number,

            },
            "tokens": tokens
        }, status=status.HTTP_200_OK)




class PropertyListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow landlords to see their own properties; tenants see all
        user = self.request.user
        if user.role == 'landlord':
            return Property.objects.filter(landlord=user)
        return Property.objects.all()

    def perform_create(self, serializer):
        serializer.save(landlord=self.request.user)


class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Landlords see all rooms for their properties; tenants see available rooms only
        user = self.request.user
        if user.role == 'landlord':
            return Room.objects.filter(property__landlord=user)
        return Room.objects.filter(is_available=True)

    def perform_create(self, serializer):
        # Ensure room creation is only allowed by the landlord for their properties
        property_id = self.request.data.get('property')
        property_instance = Property.objects.get(id=property_id)
        if property_instance.landlord != self.request.user:
            raise serializers.ValidationError("You are not allowed to add rooms to this property.")
        serializer.save(property=property_instance)



# core/views.py



class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user)

class InvoiceDetailView(generics.RetrieveAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Ensure tenants can only see their invoices
        return Invoice.objects.filter(payment__tenant=user)





class InitiatePaymentView(APIView):
    def post(self, request):
        user = request.user
        room_id = request.data.get('room')
        room = Room.objects.get(id=room_id)

        # Check that the room is available and amount is correct
        if not room.is_available:
            return Response({"error": "Room is no longer available"}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get('amount')
        if float(amount) != float(room.price):
            return Response({"error": "Amount does not match room price"}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare the payment payload
        payment_data = {
            "tx_ref": f"{user.id}_{room_id}_{room.price}",
            "amount": amount,
            "currency": "USD",
            "redirect_url": "http://localhost:8000/api/auth/flutterwave-callback/",
            "payment_type": "card",
            "customer": {
                "email": user.email,
                "phonenumber": user.profile.phone_number,
                "name": f"{user.first_name} {user.last_name}"
            },
            "customizations": {
                "title": "Room Booking Payment",
                "description": f"Payment for room {room.number} in {room.property.title}"
            }
        }

        # Make a request to Flutterwave to initialize the payment
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }
        url = f"{settings.FLUTTERWAVE_BASE_URL}/payments"
        response = requests.post(url, json=payment_data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            payment_link = response_data['data']['link']
            
            # Optionally, create a payment record in the database (in pending state)
            Payment.objects.create(
                tenant=user,
                room=room,
                amount=room.price,
                status='pending'
            )
            
            return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FlutterwaveCallbackView(APIView):
    def get(self, request):
        transaction_id = request.GET.get('transaction_id')
        tx_ref = request.GET.get('tx_ref')
        
        # Verify the payment with Flutterwave
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }
        url = f"{settings.FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/verify"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success' and data['data']['status'] == 'successful':
                # Parse room and tenant from tx_ref
                user_id, room_id, _ = tx_ref.split('_')
                room = Room.objects.get(id=room_id)
                user = request.user  # Or fetch based on user_id if needed
                
                # Update room status and create a confirmed payment record
                room.is_available = False
                room.tenant = user
                room.save()
                
                Payment.objects.filter(tx_ref=tx_ref).update(status='success', transaction_id=transaction_id)

                return Response({"status": "Payment successful"}, status=status.HTTP_200_OK)
        return Response({"status": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)
