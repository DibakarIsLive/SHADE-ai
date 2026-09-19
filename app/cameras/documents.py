"""MongoEngine documents for camera sources."""

from datetime import datetime
from uuid import uuid4

from mongoengine import BooleanField, DateTimeField, Document, StringField


class Camera(Document):
    """A configured input source; raw frames are never stored by this document."""

    camera_id = StringField(required=True, unique=True, default=lambda: str(uuid4()))
    name = StringField(required=True, max_length=120)
    source_type = StringField(
        required=True,
        choices=("webcam", "rtsp", "video_file", "synthetic"),
        default="webcam",
    )
    source_uri = StringField(default="", max_length=500)
    location = StringField(default="", max_length=180)
    enabled = BooleanField(default=True)
    status = StringField(default="configured", max_length=32)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "cameras",
        "indexes": ["camera_id", "enabled", "-created_at"],
    }

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
