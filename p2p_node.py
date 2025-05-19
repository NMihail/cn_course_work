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
        # Переменные для обработки файлов
        expected_file_size = -1
        current_file_name = None
        current_file_data = b""

        while self.running:
            try:
                # Получаем данные от клиента
                data = conn.recv(4096)
                if not data:
                    break

                buffer += data

                # Обрабатываем все возможные сообщения в буфере
                while True:
                    # Приоритет обработки файлов (если мы в процессе приёма файла)
                    if expected_file_size != -1:
                        bytes_needed = expected_file_size - len(current_file_data)
                        chunk = buffer[:bytes_needed]
                        current_file_data += chunk
                        buffer = buffer[bytes_needed:]

                        # Проверяем, полностью ли получен файл
                        if len(current_file_data) == expected_file_size:
                            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                            file_path = os.path.join(desktop, current_file_name)

                            try:
                                with open(file_path, "wb") as f:
                                    f.write(current_file_data)
                                self.gui_message_callback(f"Получен файл: {current_file_name}\n")
                            except Exception as e:
                                self.gui_message_callback(f"Ошибка сохранения файла: {str(e)}\n")

                            # Сбрасываем состояние файла
                            expected_file_size = -1
                            current_file_name = None
                            current_file_data = b""

                        # Если буфер опустел - выходим из цикла
                        if not buffer:
                            break
                        else:
                            continue  # Продолжаем обработку оставшихся данных

                    # Поиск заголовков сообщений
                    text_header_pos = buffer.find(b"TEXT:")
                    file_header_pos = buffer.find(b"FILE:")

                    # Определяем тип следующего сообщения
                    if text_header_pos == -1 and file_header_pos == -1:
                        break  # Нет сообщений для обработки

                    # Выбираем ближайший заголовок
                    headers = []
                    if text_header_pos != -1:
                        headers.append(("TEXT", text_header_pos))
                    if file_header_pos != -1:
                        headers.append(("FILE", file_header_pos))

                    # Сортируем по позиции
                    headers.sort(key=lambda x: x[1])
                    next_msg_type, header_pos = headers[0]

                    # Обрабатываем данные до заголовка как мусор (если есть)
                    if header_pos > 0:
                        self.gui_message_callback(f"Получены неопознанные данные: {buffer[:header_pos]}\n")
                        buffer = buffer[header_pos:]

                    # Обработка текстового сообщения
                    if next_msg_type == "TEXT":
                        text_end = buffer.find(b"TEXT:", 5)
                        if text_end == -1:
                            text_end = buffer.find(b"FILE:", 5)

                        if text_end == -1:  # Текст до конца буфера
                            text_data = buffer[5:]
                            buffer = b""
                        else:
                            text_data = buffer[5:text_end]
                            buffer = buffer[text_end:]

                        try:
                            text = text_data.decode("utf-8")
                            self.gui_message_callback(f"Получено: {text}\n")
                        except UnicodeDecodeError:
                            self.gui_message_callback("Ошибка декодирования текста\n")

                    # Обработка файла
                    elif next_msg_type == "FILE":
                        # Формат: FILE:filename:size:
                        rest = buffer[5:]  # Пропускаем "FILE:"

                        # Парсим имя файла
                        colon1 = rest.find(b":")
                        if colon1 == -1:
                            buffer = rest  # Ждём больше данных
                            break

                        filename = rest[:colon1].decode()

                        # Парсим размер файла
                        colon2 = rest.find(b":", colon1 + 1)
                        if colon2 == -1:
                            buffer = rest  # Ждём больше данных
                            break

                        try:
                            file_size = int(rest[colon1 + 1:colon2])
                        except ValueError:
                            self.gui_message_callback("Неверный формат размера файла\n")
                            buffer = rest[colon2 + 1:]
                            continue

                        # Вычисляем начало данных
                        data_start = colon2 + 1
                        file_data = rest[data_start:]

                        # Сохраняем состояние файла
                        expected_file_size = file_size
                        current_file_name = filename
                        current_file_data = file_data
                        buffer = b""  # Весь остаток буфера уже обработан

                        # Выходим из цикла для обработки файла в основном цикле
                        break

            except socket.error as e:
                if e.errno not in [10053, 10054]:
                    self.gui_message_callback(f"Ошибка соединения: {str(e)}\n")
                break
            except Exception as e:
                self.gui_message_callback(f"Критическая ошибка: {str(e)}\n")
                break

        # Закрытие соединения и очистка
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
        # Добавляем разделитель конца сообщения
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
            header = f"FILE:{filename}:{len(file_data)}:".encode("utf-8")
            full_data = header + file_data

            targets = target_connections or self.connections.copy()
            for connection in targets:
                try:
                    # Для больших файлов можно добавить чанкованную отправку:
                    connection['conn'].sendall(full_data)
                except BrokenPipeError:
                    self.connections.remove(connection)
                    self.gui_update_connections()
                except Exception as e:
                    self.gui_message_callback(f"Ошибка отправки: {str(e)}\n")

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
