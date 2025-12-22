"""
Security middleware for adding HTTP security headers.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to responses.
    Only applies in production (when DEBUG=False).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add security headers in production
        if not settings.DEBUG:
            # Content Security Policy
            # API backend - restrictive CSP since we don't serve HTML
            response['Content-Security-Policy'] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'none'"
            )

            # Permissions Policy (formerly Feature-Policy)
            response['Permissions-Policy'] = (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )

        return response
