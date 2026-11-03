from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import HttpResponse
from django.core.mail import EmailMessage

import os

from dotenv import load_dotenv

load_dotenv()

@api_view(['POST'])
# The public contact form is used by anonymous visitors; the project-wide
# IsAuthenticated default rejected every one of them with a 401. The default
# anonymous rate throttle still applies.
@permission_classes([AllowAny])
def send_email(request):
    data = request.data
    
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")
    
    if not name or not email or not message:
        return HttpResponse(''' <div class="form-response error">
                                    <p>Information is missing! Please try again.</p>
                                </div>''')

    # Newlines in a header value are rejected by Django; flatten the name so a
    # stray line break in the form field cannot fail the whole send.
    subject_name = " ".join(str(name).split())

    try:
        EmailMessage(
            subject=f"Website: Inquiry from {subject_name}",
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
            from_email=os.getenv("SENDER_EMAIL"),
            to=[os.getenv("RECEIVER_EMAIL", "omivernutrition@gmail.com")],
            # Replying to the notification goes straight to the visitor.
            reply_to=[email],
        ).send(fail_silently=False)
        return HttpResponse(''' <div class="form-response success">
                                    <p>Thank you! Your email has been sent successfully.</p>
                                </div>''')
    except Exception as e:
        return HttpResponse(f'''<div class="form-response error">
                                    <p>Oops! Something went wrong. Please try again, or email us directly at omivernutrition@gmail.com.</p>
                                </div>''')