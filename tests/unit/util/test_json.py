"""json.py unit tests."""
import json

from sbws.util.json import CustomDecoder, CustomEncoder

STATE = """{
    "min_perc_reached": null,
    "recent_consensus_count": [
        "2020-03-04T10:00:00",
        "2020-03-05T10:00:00",
        "2020-03-06T10:00:00"
    ],
    "recent_measurement_attempt": [
        [
            "2020-03-04T10:00:00",
            2
        ],
        [
            "2020-03-05T10:00:00",
            2
        ],
        [
            "2020-03-06T10:00:00",
            2
        ]
    ],
    "recent_priority_list": [
        "2020-03-04T10:00:00",
        "2020-03-05T10:00:00",
        "2020-03-06T10:00:00"
    ],
    "recent_priority_relay": [
        [
            "2020-03-04T10:00:00",
            2
        ],
        [
            "2020-03-05T10:00:00",
            2
        ],
        [
            "2020-03-06T10:00:00",
            2
        ]
    ],
    "scanner_started": "2020-03-14T16:15:22",
    "uuid": "x"
}"""


def test_decode_encode_roundtrip():
    d = json.loads(STATE, cls=CustomDecoder)
    s = json.dumps(d, cls=CustomEncoder, indent=4, sort_keys=True)
    assert s == STATE
