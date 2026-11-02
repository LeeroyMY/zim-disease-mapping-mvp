from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse

def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view.
    For API endpoints, returns a clean JSON error response so the frontend displays
    the exact cause. For regular browser page submissions, redirects back to login.
    """
    if request.path.startswith('/api/') or request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'status': 'error', 'message': f'CSRF validation failed: {reason}. Please refresh the page.'}, status=403)
        
    if request.user.is_authenticated:
        messages.warning(request, "Your session was interrupted or opened in another tab. Please try your action again.")
        return redirect('dashboard_root')
    else:
        messages.warning(request, "Your login session expired. Please refresh the page or try logging in again.")
        return redirect('login')
