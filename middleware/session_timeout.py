import time
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = 300  # 5 minutes

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = time.time()
            last_activity = request.session.get('last_activity')

            if last_activity:
                elapsed = current_time - last_activity

                if elapsed > self.timeout:
                    from django.contrib.auth import logout
                    logout(request)
                    messages.warning(request, "Session expired due to inactivity. Please login again.")
                    return redirect('login')  # change to your login URL name

            # update last activity
            request.session['last_activity'] = current_time

        response = self.get_response(request)
        return response