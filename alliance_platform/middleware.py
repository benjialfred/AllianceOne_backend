import logging
import traceback
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

# Configurer un logger pour les erreurs spécifiques
error_logger = logging.getLogger('alliance_errors')
error_logger.setLevel(logging.ERROR)

# S'assurer qu'il écrit dans un fichier errors.log
handler = logging.FileHandler('errors.log')
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
error_logger.addHandler(handler)

class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Intercepte les erreurs 500 et logue le traceback.
    Peut également intercepter les réponses de statut 400, 401, 404
    pour traquer d'autres comportements inattendus.
    """
    
    def process_exception(self, request, exception):
        # Ceci est appelé quand une vue lève une exception non gérée (500)
        user = request.user.username if request.user.is_authenticated else 'Anonyme'
        path = request.path
        method = request.method
        
        error_msg = f"Exception 500 sur {method} {path} par {user}\n"
        error_msg += f"Exception: {str(exception)}\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}"
        
        error_logger.error(error_msg)
        # Laisser Django retourner sa réponse 500 normale
        return None

    def process_response(self, request, response):
        # Traquer les erreurs HTTP autres que 500 retournées par DRF ou Django
        if response.status_code in [400, 401, 403, 404, 500]:
            user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'Anonyme'
            path = request.path
            method = request.method
            
            error_msg = f"Erreur {response.status_code} sur {method} {path} par {user}"
            try:
                # Essayer de logger le contenu de la réponse (utile pour les 400 de DRF)
                if hasattr(response, 'content'):
                    error_msg += f"\nDétails: {response.content.decode('utf-8')[:500]}"
            except:
                pass
                
            error_logger.error(error_msg)
            
        return response
