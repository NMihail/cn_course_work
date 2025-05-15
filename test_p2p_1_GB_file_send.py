import unittest
import threading
import time
from p2p_node import P2PNode


class TestP2PStress(unittest.TestCase):
    def setUp(self):
        self.host = f"127.0.0.1"
        self.port = 5010
        self.node = P2PNode(self.host, self.port, lambda msg: None, lambda: None)
        self.node.start_server()
        time.sleep(1)

    """def test_many_clients_connect(self):
        clients = []
        for i in range(50):  # Можно увеличить до 100+
            c = P2PNode(f"127.0.0.1", 5011 + i, lambda msg: None, lambda: None)
            c.start_server()
            time.sleep(0.05)
            c.connect_to_peer(self.host, self.port)
            clients.append(c)

        time.sleep(2)
        self.assertGreaterEqual(len(self.node.connections), 40)"""

    def test_large_file_transfer(self):
        large_data = b"x" * 1_000_000_000  # 1 GB

        def receiver_log(msg): self.received.append(msg)

        self.received = []
        sender = P2PNode('127.0.0.1', 5030, lambda msg: None, lambda: None)
        receiver = P2PNode('127.0.0.1', 5031, receiver_log, lambda: None)

        receiver.start_server()
        sender.start_server()
        time.sleep(1)
        sender.connect_to_peer("127.0.0.1", 5031)

        test_file = "testfile.bin"
        with open(test_file, "wb") as f:
            f.write(large_data)

        time.sleep(1)
        sender.send_file(test_file)

        time.sleep(60)
        assert any("Получен файл" in msg for msg in self.received)

    def tearDown(self):
        for conn in self.node.connections:
            conn['conn'].close()


if __name__ == '__main__':
    unittest.main()