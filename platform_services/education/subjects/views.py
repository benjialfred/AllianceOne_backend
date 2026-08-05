from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


from .models import Subject
from .serializers import SubjectSerializer


class SubjectViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
