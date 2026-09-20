from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from unittest.mock import patch
from platform_services.alliance_ai.models.conversation import AIConversationModel, AIMessageModel
from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel

User = get_user_model()


class AIConversationTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(email="alice@test.com")
        self.user2 = User.objects.create(email="bob@test.com")
        self.client.force_authenticate(user=self.user1)

    def test_list_conversations_empty(self):
        url = reverse('ai-conversations-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["conversations"], [])

    def test_create_and_list_conversations(self):
        url = reverse('ai-conversations-list')
        post_res = self.client.post(url, {
            "title": "Analyse financière T3",
            "organization_id": "org-alpha"
        }, format="json")
        self.assertEqual(post_res.status_code, 201)
        conv_id = post_res.data["conversation"]["id"]
        self.assertEqual(post_res.data["conversation"]["title"], "Analyse financière T3")

        # List should contain it
        list_res = self.client.get(url)
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(list_res.data["count"], 1)
        self.assertEqual(list_res.data["conversations"][0]["id"], conv_id)
        self.assertEqual(list_res.data["conversations"][0]["title"], "Analyse financière T3")

    def test_get_conversation_detail_with_messages(self):
        conv = AIConversationModel.objects.create(
            user=self.user1,
            organization_id="org-alpha",
            title="Session d'audit"
        )
        plan = ExecutionPlanModel.objects.create(
            plan_id="plan-audit-999",
            user_request="Vérifier les stocks",
            organization_id="org-alpha",
            status="SUCCEEDED"
        )
        msg1 = AIMessageModel.objects.create(
            conversation=conv,
            sender=AIMessageModel.SENDER_USER,
            content="Quel est l'état des stocks ?"
        )
        msg2 = AIMessageModel.objects.create(
            conversation=conv,
            sender=AIMessageModel.SENDER_ASSISTANT,
            content="Voici l'analyse des stocks faibles.",
            interaction_mode="MISSION",
            mission=plan,
            structured_blocks=[
                {"type": "metric", "value": "12", "label": "Articles critiques"}
            ]
        )

        url = reverse('ai-conversations-detail', kwargs={'conversation_id': str(conv.id)})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["conversation"]["id"], str(conv.id))
        self.assertEqual(len(res.data["conversation"]["messages"]), 2)
        
        # Verify message attributes
        first_msg = res.data["conversation"]["messages"][0]
        self.assertEqual(first_msg["sender"], "USER")
        self.assertEqual(first_msg["content"], "Quel est l'état des stocks ?")

        second_msg = res.data["conversation"]["messages"][1]
        self.assertEqual(second_msg["sender"], "ASSISTANT")
        self.assertEqual(second_msg["mission_id"], "plan-audit-999")
        self.assertEqual(second_msg["mission_status"], "SUCCEEDED")
        self.assertEqual(len(second_msg["structured_blocks"]), 1)

    def test_patch_and_delete_conversation(self):
        conv = AIConversationModel.objects.create(
            user=self.user1,
            organization_id="org-alpha",
            title="Initial Title"
        )
        url = reverse('ai-conversations-detail', kwargs={'conversation_id': str(conv.id)})

        # Patch title and is_pinned
        patch_res = self.client.patch(url, {"title": "Renamed Title", "is_pinned": True}, format="json")
        self.assertEqual(patch_res.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.title, "Renamed Title")
        self.assertTrue(conv.is_pinned)

        # Delete
        del_res = self.client.delete(url)
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(AIConversationModel.objects.filter(id=conv.id).exists())

    def test_user_isolation(self):
        conv1 = AIConversationModel.objects.create(
            user=self.user1,
            organization_id="org-alpha",
            title="Alice's Private Session"
        )
        # Authenticate as Bob
        self.client.force_authenticate(user=self.user2)
        url = reverse('ai-conversations-detail', kwargs={'conversation_id': str(conv1.id)})
        
        # Bob cannot read Alice's conversation
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, 404)

        # Bob cannot delete Alice's conversation
        res_del = self.client.delete(url)
        self.assertEqual(res_del.status_code, 404)
        self.assertTrue(AIConversationModel.objects.filter(id=conv1.id).exists())

    @patch("platform_services.alliance_ai.views.AllianceAIGateway.ask")
    def test_ask_view_auto_persists_session_and_messages(self, mock_ask):
        mock_ask.return_value = {
            "status": "SUCCESS",
            "plan_id": "plan-fast-track",
            "content": "Bonjour ! Je suis Alliance AI.",
            "data": {"type": "chat", "content": "Bonjour ! Je suis Alliance AI."}
        }

        url = reverse('ai-ask')
        # 1. Ask without conversation_id -> creates new session
        res = self.client.post(url, {
            "prompt": "Bonjour, présente-toi",
            "context": {"organization_id": "org-test"}
        }, format="json")

        self.assertEqual(res.status_code, 200)
        self.assertIn("conversation_id", res.data)
        self.assertIn("message_id", res.data)
        conv_id = res.data["conversation_id"]

        # Verify DB records
        conv = AIConversationModel.objects.get(id=conv_id)
        self.assertEqual(conv.user, self.user1)
        self.assertEqual(conv.messages.count(), 2)

        user_msg = conv.messages.filter(sender="USER").first()
        assistant_msg = conv.messages.filter(sender="ASSISTANT").first()
        self.assertIsNotNone(user_msg)
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(user_msg.content, "Bonjour, présente-toi")
        self.assertEqual(assistant_msg.content, "Bonjour ! Je suis Alliance AI.")

        # 2. Ask again with the same conversation_id -> appends to session
        mock_ask.return_value = {
            "status": "SUCCESS",
            "plan_id": "plan-turn-2",
            "content": "J'ai 3 élèves en retard.",
            "data": {"type": "chat", "content": "J'ai 3 élèves en retard."}
        }
        res2 = self.client.post(url, {
            "prompt": "Combien d'élèves en retard ?",
            "conversation_id": conv_id,
            "context": {"organization_id": "org-test"}
        }, format="json")

        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data["conversation_id"], conv_id)
        self.assertEqual(conv.messages.count(), 4)
