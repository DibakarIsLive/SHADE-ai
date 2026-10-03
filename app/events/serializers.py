"""Validation for emergency event records."""

from collections.abc import Mapping

from rest_framework import serializers

from events.documents import EVENT_SOURCE_TYPES


class EventProvenanceSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError("Unsupported provenance fields.")
        return super().to_internal_value(data)

    provider = serializers.CharField(max_length=120)
    model_identifier = serializers.CharField(
        max_length=200, required=False, allow_null=True, allow_blank=False
    )
    model_version = serializers.CharField(
        max_length=120, required=False, allow_null=True, allow_blank=False
    )
    artifact_sha256 = serializers.RegexField(
        regex=r"^[0-9a-fA-F]{64}$", required=False, allow_null=True
    )
    source_type = serializers.ChoiceField(choices=EVENT_SOURCE_TYPES)
    camera_id = serializers.CharField(max_length=120)
    processed_at = serializers.DateTimeField()


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
    provenance = EventProvenanceSerializer(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        provenance = attrs.get("provenance")
        if provenance is not None and provenance["camera_id"].strip() != attrs["camera_id"].strip():
            raise serializers.ValidationError(
                {"provenance": {"camera_id": "Must match the event camera_id."}}
            )
        return attrs
