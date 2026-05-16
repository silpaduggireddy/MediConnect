import random
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.models import User

from .models import OTP

def phone_register(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        if not phone.isdigit() or len(phone) != 10:
            return JsonResponse({ "error": "phone number must be 10 digits"})
        username = request.POST.get("username")
        if User.objects.filter(username=phone).exists():
           return render(request, "accounts/phone_register.html", {
               "message": "The number already exists"
            })

        otp_value = str(random.randint(100000, 999999))

        request.session["username"] = username
        request.session["otp"] = otp_value




        if not phone:
            return render(request, "accounts/phone_register.html", {
                "error": "Phone number is required"
            })

        
        # invalidate old OTPs
        OTP.objects.filter(phone_number=phone, is_verified=False).delete()

        OTP.objects.create(
            phone_number=phone,
            otp=otp_value
        )

        request.session["phone"] = phone

        print(f"OTP for {phone}: {otp_value}")  # replace with SMS later
        return redirect("otp_verify")

    return render(request, "accounts/phone_register.html")


def otp_verify(request):
    phone = request.session.get("phone")
    error = None

    if not phone:
        return redirect("phone_register")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        try:
            otp_obj = OTP.objects.get(
                phone_number=phone,
                otp=entered_otp,
                is_verified=False
            )
        except OTP.DoesNotExist:
            error = "Invalid OTP"
        else:
            if otp_obj.is_expired():
                error = "OTP expired"
                otp_obj.delete()
            else:
                otp_obj.is_verified = True
                otp_obj.save()

                username = request.session.get("username")
                user, _ = User.objects.get_or_create(username=phone)
                login(request, user)

                return redirect("post_login_redirect")
    return render(request, "accounts/otp_verify.html", {"error": error})


def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("phone")

        if not phone:
            return render(request, "accounts/login.html", {
                "error": "Phone number required"
            })

        otp_value = str(random.randint(100000, 999999))

        OTP.objects.filter(
            phone_number=phone,
            is_verified=False
        ).delete()

        OTP.objects.create(
            phone_number=phone,
            otp=otp_value
        )

        request.session["phone"] = phone
        request.session["otp"] = otp_value



        print(f"LOGIN OTP for {phone}: {otp_value}")

        return redirect("otp_verify")

    return render(request, "auth/login.html")