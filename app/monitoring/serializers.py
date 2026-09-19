from rest_framework import serializers


class MonitoringStartSerializer(serializers.Serializer):
    camera_id = serializers.CharField(max_length=120)
