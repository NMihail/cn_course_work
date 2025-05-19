import socket
import threading
import pytest

from p2p_node import P2PNode

class DummyConn:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True

class DummySocket:
    def __init__(self):
        self.bound = False
        self.listening = False
        self._on_accept = None

    def bind(self, addr):
        assert addr[0] == '127.0.0.1'
        self.bound = True

    def listen(self, backlog):
        assert backlog == 5
        self.listening = True

    def accept(self):
        # simulate a single connection
        conn = DummyConn()
        addr = ('peer-host', 1234)
        return conn, addr

    def close(self):
        pass

@pytest.fixture(autouse=True)
def patch_socket(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())

def test_init():
    node = P2PNode('127.0.0.1', 5000, lambda m: None, lambda: None)
    assert node.host == '127.0.0.1'
    assert node.port == 5000
    assert node.connections == []
    assert not node.running

def test_start_and_stop_server(monkeypatch):
    received_messages = []
    def gui_msg(m): received_messages.append(m)
    def gui_upd(): pass

    node = P2PNode('127.0.0.1', 5000, gui_msg, gui_upd)
    node.start_server()
    # give thread time to accept once
    threading.Event().wait(0.1)
    # after first accept, connections list should have one entry
    assert len(node.connections) == 1
    conn_info = node.connections[0]
    assert conn_info['id'] == 'peer-host:1234'
    assert isinstance(conn_info['conn'], DummyConn)
    # stop server
    node.running = False

def test_close_connection_success(monkeypatch):
    msgs = []
    upd = []
    node = P2PNode('h', 1, lambda m: msgs.append(m), lambda: upd.append(True))
    dummy = DummyConn()
    node.connections = [{'id': 'peer1:1000', 'conn': dummy}]
    assert node.close_connection('peer1:1000')
    assert dummy.closed
    assert 'закрыто' in msgs[0]
    assert upd

def test_close_connection_fail():
    node = P2PNode('h', 1, lambda m: None, lambda: None)
    assert not node.close_connection('nonexistent')
