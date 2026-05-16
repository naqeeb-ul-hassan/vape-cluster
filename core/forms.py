# forms.py
# Simplified forms for Vape Cluster project
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import ContactMessage, Newsletter, Review, Order

User = get_user_model()

class SignupForm(UserCreationForm):
    full_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('email', 'full_name')

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-control-custom', 'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control-custom', 'placeholder': '********'}))

class ProductForm(forms.ModelForm):
    # This will be used in the custom admin dashboard to add/edit products
    class Meta:
        from .models import Product
        model = Product
        fields = '__all__'

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['email']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['total_amount', 'shipping_address']