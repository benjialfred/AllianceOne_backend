from django.db import models

class ExecutionPlanModel(models.Model):
    plan_id = models.CharField(max_length=100, unique=True, primary_key=True)
    user_request = models.TextField()
    organization_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    final_result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alliance_ai_execution_plans"


class ExecutionStepModel(models.Model):
    step_id = models.CharField(max_length=100, unique=True, primary_key=True)
    plan = models.ForeignKey(ExecutionPlanModel, on_delete=models.CASCADE, related_name='steps')
    tool_name = models.CharField(max_length=200)
    arguments = models.JSONField()
    dependencies = models.JSONField(default=list)
    status = models.CharField(max_length=50)
    output = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    requires_confirmation = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=255, null=True, blank=True)
    execution_metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "alliance_ai_execution_steps"
