"""Integration tests for requests."""
import requests
import uuid

from sbws import settings
from sbws.util import requests as requests_utils


def test_make_session(conf, persistent_launch_tor, dests):
    uuid_str = str(uuid.uuid4())
    settings.init_http_headers(conf.get('scanner', 'nickname'), uuid_str,
                               str(persistent_launch_tor.get_version()))
    session = requests_utils.make_session(
        persistent_launch_tor, conf.getfloat('general', 'http_timeout'))
    assert session._timeout == conf.getfloat('general', 'http_timeout')

    # Because there is not an stream attached to a circuit, this will timeout.
    response = None
    try:
        response = session.get(dests.next().url, verify=False)
    except requests.exceptions.ConnectTimeout:
        pass
    assert response is None
