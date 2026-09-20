import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from platform_services.identity.authentication import AllianceTokenAuthentication
from .models.conversation import AIConversationModel, AIMessageModel

logger = logging.getLogger(__name__)


class AIConversationListView(APIView):
    """
    Lists and creates persistent AI conversations for the authenticated user and their active organization context.
    """
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org_id = (
            request.query_params.get('organization_id') or 
            request.headers.get('X-Tenant-Id') or 
            request.headers.get('x-tenant-id')
        )

        qs = AIConversationModel.objects.filter(user=user, is_archived=False)
        if org_id:
            qs = qs.filter(organization_id=org_id)

        conversations = []
        for conv in qs[:50]:
            last_msg = conv.messages.order_by('-created_at').first()
            conversations.append({
                "id": str(conv.id),
                "title": conv.title,
                "organization_id": conv.organization_id,
                "is_pinned": conv.is_pinned,
                "is_archived": conv.is_archived,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": conv.messages.count(),
                "last_message": {
                    "content": last_msg.content[:140] if last_msg else "",
                    "sender": last_msg.sender if last_msg else "",
                    "created_at": last_msg.created_at.isoformat() if last_msg else None
                } if last_msg else None
            })

        return Response({
            "status": "success",
            "count": len(conversations),
            "conversations": conversations
        }, status=200)

    def post(self, request):
        user = request.user
        title = request.data.get('title', 'Nouvelle session')
        org_id = (
            request.data.get('organization_id') or 
            request.headers.get('X-Tenant-Id') or 
            request.headers.get('x-tenant-id') or
            "default"
        )

        conv = AIConversationModel.objects.create(
            user=user,
            organization_id=str(org_id),
            title=title.strip() or 'Nouvelle session'
        )
        logger.info(f"Created new AI conversation '{conv.title}' ({conv.id}) for user {user.email}")

        return Response({
            "status": "success",
            "conversation": {
                "id": str(conv.id),
                "title": conv.title,
                "organization_id": conv.organization_id,
                "is_pinned": conv.is_pinned,
                "is_archived": conv.is_archived,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": 0,
                "last_message": None
            }
        }, status=201)


class AIConversationDetailView(APIView):
    """
    Retrieves, modifies, or deletes a specific persistent AI conversation and its complete message history.
    """
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        user = request.user
        try:
            conv = AIConversationModel.objects.prefetch_related('messages__mission').get(
                id=conversation_id,
                user=user
            )
        except (AIConversationModel.DoesNotExist, ValueError):
            return Response({"error": "Conversation introuvable"}, status=404)

        messages_data = []
        for msg in conv.messages.all():
            messages_data.append({
                "id": str(msg.id),
                "sender": msg.sender,
                "content": msg.content,
                "structured_blocks": msg.structured_blocks,
                "interaction_mode": msg.interaction_mode,
                "mission_id": msg.mission.plan_id if msg.mission else None,
                "mission_status": msg.mission.status if msg.mission else None,
                "metadata": msg.metadata,
                "created_at": msg.created_at.isoformat()
            })

        return Response({
            "status": "success",
            "conversation": {
                "id": str(conv.id),
                "title": conv.title,
                "organization_id": conv.organization_id,
                "is_pinned": conv.is_pinned,
                "is_archived": conv.is_archived,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "messages": messages_data
            }
        }, status=200)

    def patch(self, request, conversation_id):
        user = request.user
        try:
            conv = AIConversationModel.objects.get(id=conversation_id, user=user)
        except (AIConversationModel.DoesNotExist, ValueError):
            return Response({"error": "Conversation introuvable"}, status=404)

        data = request.data
        update_fields = []
        if 'title' in data:
            conv.title = str(data['title']).strip()
            update_fields.append('title')
        if 'is_pinned' in data:
            conv.is_pinned = bool(data['is_pinned'])
            update_fields.append('is_pinned')
        if 'is_archived' in data:
            conv.is_archived = bool(data['is_archived'])
            update_fields.append('is_archived')

        if update_fields:
            update_fields.append('updated_at')
            conv.save(update_fields=update_fields)

        return Response({
            "status": "success",
            "message": "Session mise à jour",
            "conversation": {
                "id": str(conv.id),
                "title": conv.title,
                "is_pinned": conv.is_pinned,
                "is_archived": conv.is_archived,
                "updated_at": conv.updated_at.isoformat()
            }
        }, status=200)

    def delete(self, request, conversation_id):
        user = request.user
        try:
            conv = AIConversationModel.objects.get(id=conversation_id, user=user)
        except (AIConversationModel.DoesNotExist, ValueError):
            return Response({"error": "Conversation introuvable"}, status=404)

        conv_id_str = str(conv.id)
        conv.delete()
        logger.info(f"Deleted conversation {conv_id_str} for user {user.email}")

        return Response({
            "status": "success",
            "message": "Conversation supprimée avec succès"
        }, status=200)
