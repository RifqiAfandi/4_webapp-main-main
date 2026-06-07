# counter/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.safestring import mark_safe

from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"})
    )


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        help_text="Alamat email aktif untuk login."
    )

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "captcha")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].label = "Username"
        self.fields["password1"].label = "Password"
        self.fields["password2"].label = "Konfirmasi password"

        self.fields["password1"].help_text = mark_safe(
            "● Password tidak boleh terlalu mirip dengan informasi pribadi Anda.<br>"
            "● Password minimal 8 karakter.<br>"
            "● Password tidak boleh password yang umum digunakan.<br>"
            "● Password tidak boleh hanya berisi angka."
        )
        self.fields["password2"].help_text = "Ketik ulang password yang sama untuk konfirmasi."

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UploadImageForm(forms.Form):
    image = forms.ImageField()
