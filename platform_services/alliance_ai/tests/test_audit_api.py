from django.urls import reverse
from rest_framework.test import APITestCase
from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel, ExecutionStepModel
import pytest

class MissionAuditAPITests(APITestCase):
    def setUp(self):
        self.plan = ExecutionPlanModel.objects.create(
            plan_id="plan-123",
            user_request="test request",
            organization_id="org1",
            status="SUCCEEDED",
            final_result={"success": True}
        )
        self.step = ExecutionStepModel.objects.create(
            step_id="step-1",
            plan=self.plan,
            tool_name="test.tool",
            arguments={"arg1": 1},
            status="SUCCEEDED",
            output={"data": "ok"}
        )

    def test_get_mission_audit(self):
        url = reverse('ai-audit', kwargs={'plan_id': 'plan-123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan_id"], "plan-123")
        self.assertEqual(response.data["status"], "SUCCEEDED")
        self.assertEqual(len(response.data["steps"]), 1)
        self.assertEqual(response.data["steps"][0]["step_id"], "step-1")
        self.assertEqual(response.data["steps"][0]["tool_name"], "test.tool")

    def test_get_mission_audit_not_found(self):
        url = reverse('ai-audit', kwargs={'plan_id': 'does-not-exist'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Plan not found")
