from io import BytesIO

from django.http import FileResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_appointment_confirmation_pdf(appointment, appointments):
    buffer = BytesIO()
    page_size = landscape(A4)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=30 * mm,
        leftMargin=30 * mm,
        topMargin=26 * mm,
        bottomMargin=24 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Brand",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#565b60"),
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
    name="TableHeader",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=colors.white,
    alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="RedTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#d30000"),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5d6266"),
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading3"],
        fontName="Helvetica",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#d30000"),
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5b5f63"),
    ))
    styles.add(ParagraphStyle(
        name="Value",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#252a2e"),
    ))
    styles.add(ParagraphStyle(
        name="ValueBold",
        parent=styles["Value"],
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="GreenValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#128448"),
    ))
    styles.add(ParagraphStyle(
        name="Note",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#055160"),
    ))

    def fmt_status(value):
        return str(value or "-").upper()

    def fmt_date(value):
        if not hasattr(value, "strftime"):
            return str(value)
        return f"{value.strftime('%B')} {value.day}, {value.year}"

    def fmt_time(value):
        if not hasattr(value, "strftime"):
            return str(value)
        hour = value.hour % 12 or 12
        minute = f":{value.minute:02d}" if value.minute else ""
        suffix = "a.m." if value.hour < 12 else "p.m."
        return f"{hour}{minute} {suffix}"

    def user_label(user):
        if not user:
            return "Not provided"
        return user.get_full_name() or user.username

    total_amount = sum(appt.amount for appt in appointments)
    first = appointment

    summary = Table(
        [[
            [
                Paragraph("Confirmation Status", styles["Label"]),
                Spacer(1, 5),
                Paragraph(fmt_status(first.status), styles["GreenValue"]),
            ],
            [
                Paragraph("Payment Status", styles["Label"]),
                Spacer(1, 5),
                Paragraph(fmt_status(first.payment_status), styles["GreenValue"]),
            ],
            [
                Paragraph("Total Amount", styles["Label"]),
                Spacer(1, 5),
                Paragraph(f"Rs. {total_amount}", styles["ValueBold"]),
            ],
        ]],
        colWidths=[75 * mm, 75 * mm, 75 * mm],
        rowHeights=[23 * mm],
        hAlign="CENTER",
        spaceAfter=14,
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d9dee2")),
        ("INNERGRID", (0, 0), (-1, -1), 8, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    def detail_rows(rows):
        return [
            [Paragraph(label, styles["Label"]), Paragraph(value, styles["ValueBold"] if bold else styles["Value"])]
            for label, value, bold in rows
        ]

    doctor_details = [
        [Paragraph("Doctor Details", styles["SectionTitle"])],
        [Table(
            detail_rows([
                ("Doctor", f"Dr. {first.doctor.name}", True),
                ("Specialization", first.doctor.specialization, False),
            ]),
            colWidths=[48 * mm, 65 * mm],
        )],
    ]

    patient_details = [
        [Paragraph("Patient Details", styles["SectionTitle"])],
        [Table(
            detail_rows([
                ("Patient Name", first.patient_name, True),
                ("Contact Number", first.contact_number or "Not provided", False),
                ("Consultation Type", first.get_consultation_type_display(), False),
                ("Registered User", user_label(first.user), False),
            ]),
            colWidths=[48 * mm, 65 * mm],
        )],
    ]

    details = Table(
        [[Table(doctor_details, colWidths=[113 * mm]), Table(patient_details, colWidths=[113 * mm])]],
        colWidths=[113 * mm, 113 * mm],
        spaceAfter=16,
    )
    details.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    schedule_data = [[
    Paragraph("Patient", styles["TableHeader"]),
    Paragraph("Date", styles["TableHeader"]),
    Paragraph("Time", styles["TableHeader"]),
    Paragraph("Payment Mode", styles["TableHeader"]),
    Paragraph("Amount", styles["TableHeader"]),
    ]]

    for appt in appointments:
        schedule_data.append([
            Paragraph(appt.patient_name, styles["Value"]),
            Paragraph(fmt_date(appt.slot.date), styles["Value"]),
            Paragraph(f"{fmt_time(appt.slot.start_time)} - {fmt_time(appt.slot.end_time)}", styles["Value"]),
            Paragraph(appt.get_payment_mode_display(), styles["Value"]),
            Paragraph(f"Rs. {appt.amount}", styles["Value"]),
            ])

    schedule = Table(
        schedule_data,
        colWidths=[25 * mm, 38 * mm, 52 * mm, 48 * mm, 35 * mm, 28 * mm],
        repeatRows=1,
        spaceAfter=12,
    )
    schedule.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#212529")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dee2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (-1, 1), (-1, -1), colors.HexColor("#ffcc00")),
    ]))

    note = Table(
        [[Paragraph(
            "Please keep this confirmation for your records. For clinic visits, arrive a few minutes before the scheduled time.",
            styles["Note"],
        )]],
        colWidths=[226 * mm],
        spaceAfter=12,
    )
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#cff4fc")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#9eeaf9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story = [
        Paragraph("MEDICONNECT CLINIC", styles["Brand"]),
        Paragraph("Appointment Confirmed", styles["RedTitle"]),
        Paragraph("Your appointment details have been confirmed.", styles["Subtitle"]),
        summary,
        details,
        Paragraph("Appointment Schedule", styles["SectionTitle"]),
        schedule,
        note,
    ]

    def draw_page(canvas, document):
        width, height = page_size
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#76aa36"))
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.roundRect(8 * mm, 8 * mm, width - 16 * mm, height - 16 * mm, 8 * mm, stroke=0, fill=1)
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)

    buffer.seek(0)
    safe_patient_name = "".join(
        ch for ch in appointment.patient_name if ch.isalnum() or ch in (" ", "-", "_")
    ).strip().replace(" ", "_")
    filename = f"appointment_{appointment.id}_{safe_patient_name or 'patient'}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)
