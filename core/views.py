from django.shortcuts import redirect
from django.contrib import messages

def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view.
    Instead of showing a 403 Forbidden page, redirect the user back to the login page
    with a warning message that their session expired or they need to refresh.
    """
    # Check if the user is somehow authenticated but submitting a bad token
    if request.user.is_authenticated:
        messages.warning(request, "Your session was interrupted or opened in another tab. Please try your action again.")
        return redirect('dashboard_root')
    else:
        messages.warning(request, "Your login session expired. Please refresh the page or try logging in again.")
        return redirect('login')
