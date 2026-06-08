try:
    from twilio.rest import Client
except ImportError:
    Client = None

def send_whatsapp_message(to_number, patient_name, doctor_name, date, time):
    if Client is None:
        raise RuntimeError("Twilio is not installed. Add twilio to requirements.txt to send WhatsApp messages.")

    account_sid = "YOUR_ACCOUNT_SID"
    auth_token = "YOUR_AUTH_TOKEN"

    client = Client(account_sid, auth_token)

    message_body = f"""
Hello {patient_name},

Your appointment is confirmed.

Doctor: {doctor_name}
Date: {date}
Time: {time}

Thank you,
MediConnect
"""

    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=message_body,
        to=f'whatsapp:+91{to_number}'
    )

    return message.sid
