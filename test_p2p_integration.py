import unittest
from unittest.mock import Mock, patch
from p2p_node import P2PNode

class TestP2PIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_message = Mock()
        self.mock_update = Mock()
        self.node = P2PNode('127.0.0.1', 5000, self.mock_message, self.mock_update)

    def test_send_text(self):
        mock_conn = Mock()
        self.node.connections = [{'conn': mock_conn, 'id': 'id', 'address': ('127.0.0.1', 1234)}]
        self.node.send_text("Hello")
        mock_conn.sendall.assert_called_once_with(b"TEXT:Hello")

    def test_send_file(self):
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"data")) as mock_file:
            mock_conn = Mock()
            self.node.connections = [{'conn': mock_conn, 'id': 'id', 'address': ('127.0.0.1', 1234)}]
            self.node.send_file("test.txt")
            self.assertIn(b"FILE:test.txt:", mock_conn.sendall.call_args[0][0])

if __name__ == '__main__':
    unittest.main()