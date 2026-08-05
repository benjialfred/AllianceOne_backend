import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve

logger = logging.getLogger(__name__)

class EducationErrorTrackingMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.path.startswith('/api/education/') and response.status_code >= 400:
            try:
                from platform_services.education.core.models import EducationErrorLog
                
                payload = ''
                if request.body:
                    try:
                        # Attempt to parse json payload, otherwise store string
                        payload = request.body.decode('utf-8')
                        payload = json.dumps(json.loads(payload))
                    except Exception:
                        payload = request.body.decode('utf-8', errors='ignore')
                        
                user_id = str(request.user.id) if request.user.is_authenticated else 'Anonymous'
                
                error_message = ''
                if hasattr(response, 'data') and response.data:
                    error_message = json.dumps(response.data)
                elif hasattr(response, 'content'):
                    error_message = response.content.decode('utf-8', errors='ignore')[:1000]

                EducationErrorLog.objects.create(
                    status_code=response.status_code,
                    path=request.path,
                    method=request.method,
                    user_identifier=user_id,
                    error_message=error_message,
                    payload=payload
                )
            except Exception as e:
                # Fallback to standard logging if DB logging fails
                logger.error(f"Failed to log education error: {e}")
                
        return response

    def process_exception(self, request, exception):
        if request.path.startswith('/api/education/'):
            try:
                from platform_services.education.core.models import EducationErrorLog
                import traceback
                
                payload = ''
                if request.body:
                    try:
                        payload = request.body.decode('utf-8')
                    except Exception:
                        payload = request.body.decode('utf-8', errors='ignore')

                user_id = str(request.user.id) if request.user.is_authenticated else 'Anonymous'
                stack_trace = traceback.format_exc()

                EducationErrorLog.objects.create(
                    status_code=500,
                    path=request.path,
                    method=request.method,
                    user_identifier=user_id,
                    error_message=str(exception),
                    stack_trace=stack_trace,
                    payload=payload
                )
            except Exception as e:
                logger.error(f"Failed to log education exception: {e}")
        return None
