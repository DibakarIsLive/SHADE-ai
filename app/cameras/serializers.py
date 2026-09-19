"""Request validation and response serialization for camera resources."""

from rest_framework import serializers


class CameraCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    source_type = serializers.ChoiceField(
        choices=("webcam", "rtsp", "video_file", "synthetic"),
        default="webcam",
    )
    source_uri = serializers.CharField(max_length=500, required=False, allow_blank=True)
    location = serializers.CharField(max_length=180, required=False, allow_blank=True)
    enabled = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs["source_type"] in {"rtsp", "video_file"} and not attrs.get("source_uri"):
            raise serializers.ValidationError(
                {"source_uri": "A URI or file path is required for this source type."}
            )
        return attrs
