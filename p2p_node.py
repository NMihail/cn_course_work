import socket
import threading
import os

class P2PNode:
    def __init__(self, host, port, gui_message_callback, gui_update_connections_callback):
        self.host = host
        self.port = port
        self.gui_message_callback = gui_message_callback
        self.gui_update_connections = gui_update_connections_callback
        self.connections = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    def start_server(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            threading.Thread(target=self._accept_connections, daemon=True).start()
            self.gui_message_callback(f"Сервер запущен на {self.host}:{self.port}\n")
        except Exception as e:
            self.gui_message_callback(f"Ошибка запуска сервера: {str(e)}\n")

    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                peer_address = (addr[0], addr[1])
                conn_id = f"{addr[0]}:{addr[1]}"
                self.connections.append({
                    'conn': conn,
                    'address': peer_address,
                    'id': conn_id
                })
                self.gui_message_callback(f"Подключен к {addr}\n")
                self.gui_update_connections()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except:
                break

    def _handle_client(self, conn):
        buffer = b""
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break

                buffer += data

                if buffer.startswith(b"TEXT:"):
                    try:
                        text = buffer[5:].decode("utf-8")
                        self.gui_message_callback(f"Получено: {text}\n")
                        buffer = b""
                    except UnicodeDecodeError:
                        continue

                elif buffer.startswith(b"FILE:"):
                    try:
                        header_end = buffer.find(b":", 5)
                        if header_end == -1: continue

                        filename = buffer[5:header_end].decode()
                        file_data = buffer[header_end + 1:]

                        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                        file_path = os.path.join(desktop, filename)

                        with open(file_path, "wb") as f:
                            f.write(file_data)

                        self.gui_message_callback(f"Получен файл: {filename}\n")
                        buffer = b""
                    except Exception as e:
                        self.gui_message_callback(f"Ошибка приема файла: {str(e)}\n")

            except socket.error as e:
                if e.errno not in [10053, 10054]:
                    self.gui_message_callback(f"Ошибка соединения: {str(e)}\n")
                break
            except Exception as e:
                self.gui_message_callback(f"Неизвестная ошибка: {str(e)}\n")
                break

        for i, connection in enumerate(self.connections.copy()):
            if connection['conn'] == conn:
                self.gui_message_callback(f"Соединение с {connection['id']} закрыто\n")
                del self.connections[i]
                self.gui_update_connections()
                break
        conn.close()

    def connect_to_peer(self, host, port):
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((host, port))
            conn_id = f"{host}:{port}"
            self.connections.append({
                'conn': conn,
                'address': (host, port),
                'id': conn_id
            })
            self.gui_message_callback(f"Подключено к {host}:{port}\n")
            self.gui_update_connections()
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
        except Exception as e:
            self.gui_message_callback(f"Ошибка подключения: {str(e)}\n")

    def send_text(self, text, target_connections=None):
        header = f"TEXT:{text}".encode("utf-8")
        targets = target_connections or self.connections.copy()
        for connection in targets:
            try:
                connection['conn'].sendall(header)
            except:
                self.connections.remove(connection)
                self.gui_update_connections()

    def send_file(self, file_path, target_connections=None):
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            filename = os.path.basename(file_path)
            header = f"FILE:{filename}:".encode("utf-8") + file_data

            targets = target_connections or self.connections.copy()
            for connection in targets:
                try:
                    connection['conn'].sendall(header)
                except:
                    self.connections.remove(connection)
                    self.gui_update_connections()

            self.gui_message_callback(f"Файл отправлен: {filename}\n")
        except Exception as e:
            self.gui_message_callback(f"Ошибка отправки файла: {str(e)}\n")

    def close_connection(self, connection_id):
        for connection in self.connections.copy():
            if connection['id'] == connection_id:
                try:
                    connection['conn'].close()
                except:
                    pass
                self.connections.remove(connection)
                self.gui_message_callback(f"Соединение с {connection_id} закрыто\n")
                self.gui_update_connections()
                return True
        return False