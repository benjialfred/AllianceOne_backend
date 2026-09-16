import hmac
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from .models import TelegramUpdateLog
from .handlers import handle_update

logger = logging.getLogger(__name__)

class TelegramWebhookView(APIView):
    """
    Secure Webhook receiver for Telegram Bot API updates.
    Enforces:
    1. Secret token header validation (X-Telegram-Bot-Api-Secret-Token)
    2. Strict JSON payload validation (Fail-Closed)
    3. Idempotent processing via TelegramUpdateLog (Prevents duplicate executions)
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Validate Secret Token Header if configured
        expected_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if expected_secret:
            received_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
            if not hmac.compare_digest(received_secret, expected_secret):
                logger.warning("Rejected Telegram webhook request: secret token mismatch or missing.")
                return Response({"error": "Forbidden: invalid secret token"}, status=403)

        # 2. Validate payload structure (Fail-Closed)
        update = request.data
        if not isinstance(update, dict):
            logger.warning("Rejected malformed non-dictionary Telegram update payload.")
            return Response({"error": "Bad Request: payload must be a JSON object"}, status=400)

        update_id = update.get("update_id")
        if update_id is None:
            logger.warning("Rejected Telegram update missing required 'update_id'.")
            return Response({"error": "Bad Request: missing 'update_id'"}, status=400)

        # 3. Idempotency Check: Prevent duplicate execution of retransmitted updates
        if TelegramUpdateLog.objects.filter(update_id=update_id).exists():
            logger.info(f"Duplicate Telegram update {update_id} received. Skipping re-execution.")
            return Response({"status": "already_processed", "update_id": update_id}, status=200)

        # Extract metadata for audit logging
        telegram_user_id = None
        command_label = ""
        if "message" in update and isinstance(update["message"], dict):
            telegram_user_id = update["message"].get("from", {}).get("id")
            command_label = (update["message"].get("text") or "")[:100]
        elif "callback_query" in update and isinstance(update["callback_query"], dict):
            telegram_user_id = update["callback_query"].get("from", {}).get("id")
            command_label = f"callback: {update['callback_query'].get('data', '')}"[:100]

        try:
            TelegramUpdateLog.objects.create(
                update_id=update_id,
                telegram_user_id=telegram_user_id,
                command=command_label,
                raw_payload=update
            )
        except Exception as e:
            logger.error(f"Failed to record TelegramUpdateLog for update {update_id}: {e}")
            # In case of DB constraint collision (race condition), treat as already processed
            return Response({"status": "already_processed", "update_id": update_id}, status=200)

        # 4. Dispatch update to handlers
        try:
            result = handle_update(update)
            return Response({"status": "ok", "update_id": update_id, "result": result}, status=200)
        except Exception as e:
            logger.error(f"Error handling Telegram update {update_id}: {e}", exc_info=True)
            # Return 200 to Telegram so it doesn't storm with repeated delivery loops on logic errors
            return Response({"status": "error_handled", "update_id": update_id, "detail": str(e)}, status=200)
