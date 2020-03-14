"""JSON custom serializers and deserializers."""
import datetime
import json

from .timestamps import DateTimeSeq, DateTimeIntSeq


class CustomEncoder(json.JSONEncoder):
    """JSONEncoder that serializes datetime to ISO 8601 string."""

    def default(self, obj):
        if isinstance(obj, DateTimeSeq) or isinstance(obj, DateTimeIntSeq):
            return [self.default(i) for i in obj.list()]
        if isinstance(obj, datetime.datetime):
            return obj.replace(microsecond=0).isoformat()
        else:
            return super().default(obj)


class CustomDecoder(json.JSONDecoder):
    """JSONDecoder that deserializes ISO 8601 string to datetime."""

    def decode(self, s, **kwargs):
        decoded = super().decode(s, **kwargs)
        return self.process(decoded)

    def process(self, obj):
        if isinstance(obj, list) and obj:
            return [self.process(item) for item in obj]
        if isinstance(obj, dict):
            return {key: self.process(value) for key, value in obj.items()}
        if isinstance(obj, str):
            try:
                return datetime.datetime.strptime(obj, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                try:
                    datetime.datetime.strptime(
                        obj, "%Y-%m-%dT%H:%M:%S.%f"
                    ).replace(microsecond=0)
                except ValueError:
                    pass
            except TypeError:
                pass
        return obj
