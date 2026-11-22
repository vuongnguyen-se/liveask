import time

import pytest
from helpers import make_room
from starlette.websockets import WebSocketDisconnect


def wait_until(condition, seconds=3.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def test_hello_names_the_pod_and_ping_gets_pong(client):
    room = make_room(client)
    with client.websocket_connect(f"/ws/rooms/{room['code']}?role=screen") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["data"]["pod"]
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}
        ws.send_text("not json")  # garbage is ignored, the socket stays up
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


def test_unknown_room_is_closed_with_4404(client):
    with client.websocket_connect("/ws/rooms/ZZZZZZ") as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
        assert info.value.code == 4404


def test_room_connection_limit(client):
    # Lower the per-room limit on the running hub (the default is 300).
    client.app.state.hub.max_per_room = 1
    room = make_room(client)
    with client.websocket_connect(f"/ws/rooms/{room['code']}") as first:
        assert first.receive_json()["type"] == "hello"
        with client.websocket_connect(f"/ws/rooms/{room['code']}") as second:
            with pytest.raises(WebSocketDisconnect) as info:
                second.receive_json()
            assert info.value.code == 1013


def test_disconnected_sockets_are_removed_from_the_hub(client):
    room = make_room(client)
    hub = client.app.state.hub
    with client.websocket_connect(f"/ws/rooms/{room['code']}") as ws:
        ws.receive_json()
        assert hub.connection_count() == 1
    assert wait_until(lambda: hub.connection_count() == 0)
    assert hub.rooms == {}


def test_readyz_needs_the_listener(client):
    assert client.get("/readyz").status_code == 200
    client.app.state.hub.listening = False
    assert client.get("/readyz").status_code == 503
    client.app.state.hub.listening = True
    client.app.state.hub.shutting_down = True
    assert client.get("/readyz").status_code == 503
    client.app.state.hub.shutting_down = False
