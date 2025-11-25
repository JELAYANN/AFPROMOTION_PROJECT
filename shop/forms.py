# shop/forms.py
from django import forms # type: ignore 
from django.contrib.auth.models import User  # type: ignore
from django.contrib.auth.forms import UserCreationForm   # type: ignore

from .models import Customer


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['phone', 'address', 'city', 'province', 'postal_code']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'phone': 'No. Telepon',
            'address': 'Alamat',
            'city': 'Kota',
            'province': 'Provinsi',
            'postal_code': 'Kode Pos',
        }


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(required=False, label="Nama Depan")
    last_name = forms.CharField(required=False, label="Nama Belakang")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]
