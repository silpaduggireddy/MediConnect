from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponseForbidden

from appointments.models import Appointment
from .models import Payment


# ----------------------------
# UI FLOW (WEB)
# ----------------------------

# @login_required
# def start_payment(request):
#     if request.method == "POST":
#         appointment_id = request.POST.get("appointment_id")
#         if not appointment_id:
#             return redirect("doctors:doctor_list")

#         return redirect("payment:payment_page", appointment_id=appointment_id)

@login_required
def payment_page(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        consultation_type="ONLINE",
        payment_status="PENDING"
    )

    return render(
        request,
        "payment/payment.html",
        {"appointment": appointment}
    )



@login_required
def confirm_payment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user
    )

    if appointment.consultation_type != "ONLINE":
        return HttpResponseForbidden("Invalid payment attempt")

    if appointment.payment_status == "PAID":
        return redirect("payment:payment_success")

    if request.method == "POST":
        method = request.POST.get("method")

        if not method:
            return redirect(
                "payment:payment_page",
                appointment_id=appointment.id
            )

        # ✅ Update appointment
        appointment.payment_mode = method
        appointment.payment_status = "PAID"
        appointment.save()

        # ✅ Create payment record
        Payment.objects.create(
            appointment=appointment,
            amount=appointment.amount,
            method=method
        )

        request.session["last_appointment_id"] = appointment.id
        return redirect("payment:payment_success")


@login_required
def payment_success(request):
    appointment_id = request.session.get("last_appointment_id")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user
    )

    return render(
        request,
        "payment/success.html",
        {"appointment": appointment}
    )


# ----------------------------
# API FLOW (SECURE)
# ----------------------------

@api_view(["POST"])
@login_required
def make_payment_api(request):
    appointment_id = request.data.get("appointment_id")
    method = request.data.get("method")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user
    )

    if appointment.payment_status == "PAID":
        return Response({"message": "Already paid"})

    appointment.payment_mode = method
    appointment.payment_status = "PAID"
    appointment.save()

    Payment.objects.create(
        appointment=appointment,
        amount=appointment.amount,
        method=method
    )

    return Response({"message": "Payment successful"})
