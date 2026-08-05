from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


from .models import Teacher
from .serializers import TeacherSerializer


class TeacherViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

