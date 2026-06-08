import random
import json
from urllib import response

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User

from .models import OTP


def phone_register(request):

    if request.method == "POST":

        phone = request.POST.get("phone")
        username = request.POST.get("username")

        # Validate phone
        if not phone or not phone.isdigit() or len(phone) != 10:

            return render(
                request,
                "accounts/phone_register.html",
                {
                    "error": "Phone number must be 10 digits"
                }
            )

        # Check existing user
        if User.objects.filter(username=phone).exists():

            return render(
                request,
                "accounts/phone_register.html",
                {
                    "message": "The number already exists"
                }
            )

        # Generate OTP
        otp_value = str(random.randint(100000, 999999))

        # Store session data
        request.session["username"] = username
        request.session["phone"] = phone
        request.session["otp"] = otp_value

        # Delete old OTPs
        OTP.objects.filter(
            phone_number=phone,
            is_verified=False
        ).delete()

        # Create new OTP
        OTP.objects.create(
            phone_number=phone,
            otp=otp_value
        )

        print(f"REGISTER OTP for {phone}: {otp_value}")

        response = redirect("otp_verify")
        response.set_cookie("test_otp", otp_value, max_age=300)

        return response

    return render(request, "accounts/phone_register.html")


def otp_verify(request):

    phone = request.session.get("phone")

    if not phone:
        return redirect("phone_register")

    error = None
    message = None

    # Resend OTP
    if request.GET.get("resend"):

        otp_value = str(random.randint(100000, 999999))

        OTP.objects.filter(
            phone_number=phone,
            is_verified=False
        ).delete()

        OTP.objects.create(
            phone_number=phone,
            otp=otp_value
        )

        request.session["otp"] = otp_value

        print(f"RESENT OTP for {phone}: {otp_value}")

        message = "New OTP sent successfully"

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

                user, created = User.objects.get_or_create(
                    username=phone,
                    defaults={
                        "first_name": username if username else ""
                    }
                )

                login(request, user)

                # Clear OTP from session
                request.session.pop("otp", None)

                return redirect("post_login_redirect")

    print("SESSION OTP =", request.session.get("otp"))
    print("PHONE =", request.session.get("phone"))

    return render(
        request,
        "accounts/otp_verify.html",
        {
            "error": error,
            "message": message
        }
    )


def login_view(request):

    if request.method == "POST":

        phone = request.POST.get("phone")

        if not phone or not phone.isdigit() or len(phone) != 10:

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Valid phone number required"
                }
            )

        if not User.objects.filter(username=phone).exists():

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Account does not exist"
                }
            )

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

        # TESTING: Show OTP in popup on otp_verify page
        response = redirect("otp_verify")
        response.set_cookie('test_otp', otp_value, max_age=300)  # 5 minutes
        return response

    return render(request, "accounts/login.html")

def check_user(request):

    if request.method == "POST":

        data = json.loads(request.body)

        mobile = data.get("mobile")

        exists = User.objects.filter(
            username=mobile
        ).exists()

        if exists:

            return JsonResponse({
                "status": "exists"
            })

        return JsonResponse({
            "status": "new"
        })

    return JsonResponse({
        "status": "invalid"
    })