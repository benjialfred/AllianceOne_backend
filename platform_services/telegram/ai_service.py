import logging
from typing import Dict, Any, Optional
from platform_services.alliance_ai.gateway.gateway import AllianceAIGateway, _orchestrator
from platform_services.alliance_ai.context.context_engine import ContextEngine
from platform_services.alliance_ai.security.approval_engine import SecurityApprovalEngine
from platform_services.alliance_ai.security.types import Decision
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.state_store import StateStore
from platform_services.alliance_ai.orchestration.verifier import VerificationEngine
from .client import TelegramClient
from .identity import resolve_telegram_identity, get_active_membership
from .keyboards import (
    get_main_menu_keyboard,
    get_connect_keyboard,
    get_ai_confirmation_keyboard,
    get_ai_quick_keyboard,
    get_help_keyboard
)

logger = logging.getLogger(__name__)

UNAUTHENTICATED_AI_MESSAGE = """⚠️ *Authentification requise pour Alliance AI* 🤖

Pour dialoguer avec *Alliance AI*, consulter vos données ou exécuter des actions, vous devez d'abord associer votre compte *Alliance One*.

*Comment associer votre compte en 1 minute ?*
1️⃣ Cliquez sur le bouton *« 🌐 Ouvrir Alliance One Web »* ci-dessous :
   https://allianceone-frontend.vercel.app/app/settings
2️⃣ Rendez-vous dans les **Paramètres** ou cliquez sur *« Bot Telegram »* dans la barre supérieure.
3️⃣ Cliquez sur *« Ouvrir Telegram & Associer Mon Compte »* (liaison en 1 clic) ou copiez le code personnel à 6 caractères (ex: `ALX-123456`).
4️⃣ Si vous avez copié le code, tapez simplement ici :
   `/connect VOTRE_CODE`
"""

def process_ai_query(
    user_id: int,
    chat_id: int,
    query_text: str,
    client: Optional[TelegramClient] = None
) -> Dict[str, Any]:
    """
    Primary handler for all conversational AI interactions originating from Telegram.
    Routes queries to AllianceAIGateway with strict tenant isolation, server-side RBAC,
    and returns rich interactive Telegram cards.
    """
    if client is None:
        client = TelegramClient()

    # 1. Identity Resolution & Verification
    identity = resolve_telegram_identity(user_id) if user_id else None
    if not identity:
        logger.info(f"Unauthenticated AI query attempt from telegram user {user_id}")
        client.send_message(chat_id, UNAUTHENTICATED_AI_MESSAGE, reply_markup=get_connect_keyboard())
        return {"status": "unauthenticated", "handled": True}

    # 2. Resolve Active Organization Context with Auto-Heal
    active_membership = get_active_membership(identity)
    if not active_membership:
        logger.warning(f"Telegram user {user_id} has no active membership in any organization")
        client.send_message(
            chat_id,
            "⚠️ *Aucune organisation active*\n\nVotre compte Alliance One n'est actuellement rattaché à aucune organisation active.",
            reply_markup=get_main_menu_keyboard(is_linked=True)
        )
        return {"status": "no_active_organization", "handled": True}

    # 3. Native Telegram Typing Indicator
    try:
        client.send_chat_action(chat_id, "typing")
    except Exception as e:
        logger.debug(f"Failed to send typing action: {e}")

    # Clean query text (strip optional /ai command prefix)
    clean_prompt = query_text
    if clean_prompt.startswith("/ai"):
        clean_prompt = clean_prompt[3:].strip()
    if not clean_prompt:
        clean_prompt = "Bonjour ! Que peux-tu faire pour mon organisation ?"

    # 4. Construct Secure Client Context
    client_context = {
        "organization_id": str(active_membership.organization_id),
        "tenant_id": str(active_membership.organization_id),
        "source": "telegram",
        "channel": "telegram",
        "chat_id": chat_id,
        "telegram_user_id": user_id,
        "active_module": "general",
    }

    logger.info(
        f"Forwarding query to AllianceAIGateway for user {identity.user.email} "
        f"(Org: {active_membership.organization.name}): '{clean_prompt[:60]}...'"
    )

    # 5. Hand off to the Single AI Gateway
    gateway_response = AllianceAIGateway.ask(
        user=identity.user,
        prompt=clean_prompt,
        client_context=client_context
    )

    if gateway_response.get("status") != "SUCCESS":
        error_content = gateway_response.get("content", "Une erreur est survenue lors de la communication avec Alliance AI.")
        client.send_message(
            chat_id,
            f"❌ *Erreur Alliance AI*\n\n{error_content}",
            reply_markup=get_ai_quick_keyboard()
        )
        return {"status": "gateway_error", "handled": True, "error": error_content}

    plan_id = gateway_response.get("plan_id")
    plan_data = gateway_response.get("data", {})
    plan_type = plan_data.get("type", "chat")

    # 6. FAST-TRACK : Conversational Chat (No tool executions needed)
    if plan_type == "chat" or not plan_id:
        chat_content = gateway_response.get("content") or plan_data.get("content", "Voici ma réponse.")
        client.send_message(chat_id, chat_content, reply_markup=get_ai_quick_keyboard())
        return {"status": "success", "type": "chat", "handled": True, "plan_id": plan_id}

    # 7. MISSION / TOOLS : Load Execution Plan and check for Sensitive Actions
    plan = StateStore.load_plan(plan_id)
    if not plan:
        # Direct fallback to response content if plan state wasn't stored
        client.send_message(
            chat_id,
            gateway_response.get("content", "Mission terminée."),
            reply_markup=get_ai_quick_keyboard()
        )
        return {"status": "success", "type": "chat_fallback", "handled": True}

    # Check for steps waiting for human confirmation
    waiting_step = next(
        (s for s in plan.steps if s.status == ExecutionStatus.WAITING_FOR_APPROVAL or s.requires_confirmation),
        None
    )

    if waiting_step:
        action_hash = waiting_step.execution_metadata.get("action_hash", "")
        args_lines = []
        if isinstance(waiting_step.arguments, dict):
            for k, v in waiting_step.arguments.items():
                args_lines.append(f"  • *{k}* : `{v}`")
        args_str = "\n".join(args_lines) if args_lines else "  • _Aucun paramètre requis_"

        confirmation_card = (
            f"⚠️ *Demande d'Autorisation Sécurisée* 🛡️\n\n"
            f"Alliance AI sollicite votre validation avant d'exécuter une opération sensible sur votre organisation :\n\n"
            f"• *Outil Système* : `{waiting_step.tool_name}`\n"
            f"• *Organisation Cible* : *{active_membership.organization.name}*\n"
            f"• *Paramètres de l'action* :\n{args_str}\n\n"
            f"• *Empreinte de sécurité (Hash)* :\n`{action_hash[:20]}...`\n\n"
            f"_Confirmez-vous l'exécution immédiate de cette opération ?_"
        )
        keyboard = get_ai_confirmation_keyboard(plan.plan_id, waiting_step.step_id, action_hash)
        client.send_message(chat_id, confirmation_card, reply_markup=keyboard)
        return {
            "status": "waiting_approval",
            "handled": True,
            "plan_id": plan.plan_id,
            "step_id": waiting_step.step_id,
            "action_hash": action_hash
        }

    # If all steps succeeded directly without requiring confirmation
    if plan.status == ExecutionStatus.SUCCEEDED:
        step_summaries = []
        for s in plan.steps:
            v_badge = "✅" if "VERIFIED" in str(s.verification_status) else "ℹ️"
            step_summaries.append(f"• `{s.tool_name}` : Succès {v_badge}")
        steps_text = "\n".join(step_summaries) if step_summaries else "Opération effectuée sans étapes complexes."

        success_message = (
            f"⚡ *Mission Exécutée avec Succès* ✨\n\n"
            f"• *Organisation* : *{active_membership.organization.name}*\n"
            f"• *Résultat* : {plan.user_request_response}\n\n"
            f"*Actions validées :*\n{steps_text}"
        )
        client.send_message(chat_id, success_message, reply_markup=get_ai_quick_keyboard())
        return {"status": "success", "type": "mission_succeeded", "handled": True, "plan_id": plan.plan_id}

    # If plan encountered a failure
    if plan.status == ExecutionStatus.FAILED:
        failed_step = next((s for s in plan.steps if s.status == ExecutionStatus.FAILED), None)
        err = failed_step.error if failed_step else "Échec de traitement"
        failure_message = (
            f"❌ *Échec de la Mission* ⚠️\n\n"
            f"• *Organisation* : *{active_membership.organization.name}*\n"
            f"• *Erreur signalée* : `{err}`\n\n"
            f"Veuillez reformuler ou contacter votre administrateur si le problème persiste."
        )
        client.send_message(chat_id, failure_message, reply_markup=get_ai_quick_keyboard())
        return {"status": "failed", "handled": True, "error": err, "plan_id": plan.plan_id}

    # Otherwise send the plan's general response
    client.send_message(
        chat_id,
        plan.user_request_response or "Votre requête a été traitée.",
        reply_markup=get_ai_quick_keyboard()
    )
    return {"status": "handled", "type": "general", "plan_id": plan.plan_id}


def handle_ai_confirm_callback(
    callback_query: Dict[str, Any],
    client: TelegramClient
) -> Dict[str, Any]:
    """
    Handles inline callback query when user clicks 'Confirmer l'action'.
    Enforces SecurityApprovalEngine revalidation with the canonical action hash,
    resumes execution via the Orchestrator, and verifies results.
    """
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    from_user = callback_query.get("from", {})
    user_id = from_user.get("id") or chat_id

    # Parse callback payload: ai_confirm:<plan_id>:<step_id>:<action_hash>
    parts = data.split(":", 3)
    if len(parts) < 4:
        if query_id:
            client.answer_callback_query(query_id, text="Données d'autorisation invalides.", show_alert=True)
        return {"status": "error", "reason": "invalid_callback_data"}

    _, plan_id, step_id, action_hash = parts

    # 1. Verify User Identity
    identity = resolve_telegram_identity(user_id) if user_id else None
    if not identity:
        if query_id:
            client.answer_callback_query(query_id, text="Authentification requise.", show_alert=True)
        return {"status": "error", "reason": "unauthenticated"}

    # 2. Load Plan and Target Step
    plan = StateStore.load_plan(plan_id)
    if not plan:
        if query_id:
            client.answer_callback_query(query_id, text="Mission introuvable ou expirée.", show_alert=True)
        return {"status": "error", "reason": "plan_not_found"}

    step = plan.get_step(step_id)
    if not step:
        if query_id:
            client.answer_callback_query(query_id, text="Étape introuvable dans le plan.", show_alert=True)
        return {"status": "error", "reason": "step_not_found"}

    if step.status != ExecutionStatus.WAITING_FOR_APPROVAL:
        if query_id:
            client.answer_callback_query(query_id, text="Cette action a déjà été traitée.")
        return {"status": "already_processed", "step_status": step.status.value}

    # 3. Security Revalidation with Canonical Action Hash (Requirement Step 8)
    context = ContextEngine.build_context(
        identity.user,
        {"organization_id": str(identity.active_organization_id or plan.organization_id)}
    )

    revalidation = SecurityApprovalEngine.revalidate_confirmation(
        tool_name=step.tool_name,
        arguments=step.arguments,
        context=context,
        mission_id=plan.plan_id,
        provided_hash=action_hash
    )

    if revalidation.decision != Decision.ALLOW:
        logger.warning(f"Security Gate revalidation failed for step {step_id}: {revalidation.reason_code}")
        if query_id:
            client.answer_callback_query(
                query_id,
                text=f"Refus de sécurité : {revalidation.reason_code}",
                show_alert=True
            )
        step.status = ExecutionStatus.FAILED
        step.error = f"Revalidation refusée : {revalidation.reason_code}"
        plan.status = ExecutionStatus.FAILED
        StateStore.save_plan(plan)

        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⛔ *Sécurité : Action Refusée*\n\nL'autorisation a échoué lors de la vérification finale : `{revalidation.reason_code}`.",
            reply_markup=get_ai_quick_keyboard()
        )
        return {"status": "security_deny", "reason": revalidation.reason_code}

    # 4. Acknowledge Telegram callback immediately (< 200ms)
    if query_id:
        client.answer_callback_query(query_id, text="Action confirmée ! Exécution en cours...")

    # 5. Resume execution with validated confirmation hash
    step.execution_metadata["confirmation_hash"] = action_hash
    step.status = ExecutionStatus.PENDING
    step.requires_confirmation = False
    StateStore.save_plan(plan)

    _orchestrator.resume_plan(plan, context)

    # 6. Verify and Report Result
    reloaded_plan = StateStore.load_plan(plan_id)
    updated_step = reloaded_plan.get_step(step_id) if reloaded_plan else step

    if updated_step.status == ExecutionStatus.SUCCEEDED:
        v_status = "Vérifiée et intègre ✅" if "VERIFIED" in str(updated_step.verification_status) else "Exécutée ✅"
        result_text = (
            f"✅ *Action Confirmée et Exécutée avec Succès !* 🎉\n\n"
            f"• *Outil Système* : `{updated_step.tool_name}`\n"
            f"• *Organisation* : *{context.organization_name}*\n"
            f"• *Contrôle de validation* : {v_status}\n"
            f"• *Statut* : Opération terminée avec succès"
        )
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            reply_markup=get_ai_quick_keyboard()
        )
        return {"status": "success", "executed": True, "step_id": step_id}
    else:
        err_msg = updated_step.error or "Erreur inconnue lors de l'exécution"
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ *Échec lors de l'exécution de l'action :*\n\n`{err_msg}`",
            reply_markup=get_ai_quick_keyboard()
        )
        return {"status": "execution_failed", "error": err_msg}


def handle_ai_cancel_callback(
    callback_query: Dict[str, Any],
    client: TelegramClient
) -> Dict[str, Any]:
    """
    Handles inline callback query when user clicks 'Annuler'.
    Marks the step and plan as cancelled.
    """
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    from_user = callback_query.get("from", {})
    user_id = from_user.get("id") or chat_id

    parts = data.split(":", 2)
    if len(parts) < 3:
        if query_id:
            client.answer_callback_query(query_id, text="Action invalide.")
        return {"status": "error", "reason": "invalid_data"}

    _, plan_id, step_id = parts

    # Mark plan and step as cancelled
    plan = StateStore.load_plan(plan_id)
    if plan:
        step = plan.get_step(step_id)
        if step and step.status == ExecutionStatus.WAITING_FOR_APPROVAL:
            step.status = ExecutionStatus.FAILED
            step.error = "Opération annulée par l'utilisateur sur Telegram."
            plan.status = ExecutionStatus.FAILED
            StateStore.save_plan(plan)

    if query_id:
        client.answer_callback_query(query_id, text="Action annulée.")

    client.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="🚫 *Action annulée.*\n\nAucune modification n'a été apportée à votre organisation.",
        reply_markup=get_ai_quick_keyboard()
    )
    return {"status": "cancelled", "plan_id": plan_id}
