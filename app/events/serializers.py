"""Validation for emergency event records."""

from rest_framework import serializers


class EventCreateSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=80)
    severity = serializers.ChoiceField(choices=("info", "warning", "critical"))
    status = serializers.ChoiceField(
        choices=("detected", "verified", "acknowledged", "resolved"),
        default="verified",
    )
    camera_id = serializers.CharField(max_length=120)
    track_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.0)
    duration_seconds = serializers.FloatField(min_value=0.0, default=0.0)
    frame_count = serializers.IntegerField(min_value=0, default=0)
    evidence_uri = serializers.CharField(max_length=500, required=False, allow_blank=True)
    context = serializers.DictField(required=False, default=dict)
