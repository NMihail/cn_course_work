import unittest
from unittest.mock import Mock
from p2p_node import P2PNode


class TestP2PNodeMultipleConnections(unittest.TestCase):
    def setUp(self):
        self.mock_message = Mock()
        self.mock_update = Mock()
        self.node = P2PNode('127.0.0.1', 5000, self.mock_message, self.mock_update)
        # Генерируем 50 мок-соединений
        self.connections = []
        for i in range(50):
            mock_conn = Mock()
            conn_id = f"conn_{i}"
            address = ('127.0.0.1', 5001 + i)
            self.connections.append({
                'conn': mock_conn,
                'id': conn_id,
                'address': address
            })

    def test_handle_50_connections(self):
        # Добавляем все 50 соединений в узел
        self.node.connections = self.connections.copy()

        # Проверяем количество подключений
        self.assertEqual(len(self.node.connections), 50)

    def test_send_message_to_all_connections(self):
        self.node.connections = self.connections.copy()
        test_message = "Stress test message"

        # Отправляем сообщение всем
        self.node.send_text(test_message)

        # Проверяем, что sendall вызван для каждого соединения
        expected_data = f"TEXT:{test_message}".encode()
        for conn_info in self.connections:
            conn_info['conn'].sendall.assert_called_once_with(expected_data)

    def test_close_all_connections(self):
        self.node.connections = self.connections.copy()

        # Закрываем все соединения
        for conn_info in self.connections:
            self.node.close_connection(conn_info['id'])
            conn_info['conn'].close.assert_called_once()

        # Проверяем, что все соединения удалены
        self.assertEqual(len(self.node.connections), 0)


if __name__ == '__main__':
    unittest.main()