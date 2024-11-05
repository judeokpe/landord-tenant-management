

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Property, Room
from .models import Payment, Invoice, Room


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'role', 'phone_number',)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password doesn't match."})
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            role=validated_data['role'],
            phone_number =validated_data['phone_number']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = User.objects.filter(email=email).first()
            if user is None or not user.check_password(password):
                raise serializers.ValidationError("Invalid credentials.")
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
    
    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }







class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'number', 'price', 'is_available', 'tenant')

class PropertySerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = ('id', 'title', 'address', 'city', 'state', 'description', 'created_at', 'rooms')






class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'tenant', 'room', 'amount', 'date_paid', 'transaction_id', 'status')
        read_only_fields = ('tenant', 'transaction_id', 'status', 'date_paid')

    def validate(self, data):
        room = data['room']
        if not room.is_available:
            raise serializers.ValidationError("This room is no longer available.")
        if data['amount'] != room.price:
            raise serializers.ValidationError("The amount does not match the room price.")
        return data

    def create(self, validated_data):
        # Set the tenant as the logged-in user
        validated_data['tenant'] = self.context['request'].user
        payment = super().create(validated_data)
        
        # Mark room as unavailable and save the room's status
        room = validated_data['room']
        room.is_available = False
        room.tenant = validated_data['tenant']
        room.save()
        
        # Automatically generate an invoice for this payment
        Invoice.objects.create(payment=payment, amount=validated_data['amount'])
        return payment

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'payment', 'date_issued', 'amount')
