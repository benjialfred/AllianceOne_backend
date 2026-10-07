import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def contact_api_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Simulate processing/saving the contact form submission
            email = data.get('email', '')
            msg_type = data.get('type', '')
            message = data.get('message', '')
            
            print(f"--- NOUVEAU MESSAGE DE CONTACT ---")
            print(f"De: {email}\nType: {msg_type}\nMessage: {message}")
            print(f"----------------------------------")
            
            return JsonResponse({"status": "success", "message": "Votre message a été bien reçu."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": "Erreur lors du traitement."}, status=400)
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
