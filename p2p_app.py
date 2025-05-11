import socket
import threading
import tkinter as tk
import os
from tkinter import ttk, scrolledtext, messagebox, filedialog


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


class P2PGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Messenger")
        self.root.geometry("800x600")

        self.node = None
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = 5000
        self.selected_file = None

        self.setup_ui()
        self.start_node()

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(top_frame, text="IP:").grid(row=0, column=0, padx=5)
        self.ip_entry = ttk.Entry(top_frame, width=15)
        self.ip_entry.grid(row=0, column=1, padx=5)

        ttk.Label(top_frame, text="Порт:").grid(row=0, column=2, padx=5)
        self.port_entry = ttk.Entry(top_frame, width=7)
        self.port_entry.grid(row=0, column=3, padx=5)

        self.connect_btn = ttk.Button(top_frame, text="Подключиться", command=self.connect_to_peer)
        self.connect_btn.grid(row=0, column=4, padx=5)

        control_frame = ttk.Frame(self.root)
        control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self.file_btn = ttk.Button(control_frame, text="Выбрать файл", command=self.select_file)
        self.file_btn.pack(side=tk.LEFT, padx=5)

        self.send_file_btn = ttk.Button(control_frame, text="Отправить файл", command=self.send_file)
        self.send_file_btn.pack(side=tk.LEFT, padx=5)

        recipient_frame = ttk.Frame(control_frame)
        recipient_frame.pack(side=tk.RIGHT, padx=10)
        ttk.Label(recipient_frame, text="Получатель:").pack(side=tk.LEFT)
        self.recipient_label = ttk.Label(recipient_frame, text="Все", width=20)
        self.recipient_label.pack(side=tk.LEFT, padx=5)

        main_frame = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_frame.grid(row=2, column=0, sticky="nsew")

        history_frame = ttk.Frame(main_frame, padding=5)
        self.history = scrolledtext.ScrolledText(history_frame, state='disabled')
        self.history.pack(expand=True, fill=tk.BOTH)
        main_frame.add(history_frame, weight=2)

        connections_frame = ttk.Frame(main_frame, padding=5)

        self.connections_tree = ttk.Treeview(
            connections_frame,
            columns=("address", "port"),
            show="headings",
            height=5,
            selectmode='extended'
        )
        self.connections_tree.heading("address", text="Адрес")
        self.connections_tree.heading("port", text="Порт")
        self.connections_tree.column("address", width=150, anchor=tk.W)
        self.connections_tree.column("port", width=80, anchor=tk.W)

        scrollbar = ttk.Scrollbar(connections_frame, orient="vertical", command=self.connections_tree.yview)
        self.connections_tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(connections_frame)
        self.refresh_btn = ttk.Button(btn_frame, text="Обновить", command=self.update_connections_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        self.close_btn = ttk.Button(btn_frame, text="Закрыть выбранное", command=self.close_selected_connection)
        self.close_btn.pack(side=tk.LEFT, padx=5)

        self.connections_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        btn_frame.pack(side=tk.BOTTOM, pady=5)

        main_frame.add(connections_frame, weight=1)

        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.grid(row=3, column=0, sticky="ew")

        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(input_frame, text="Отправить", command=self.send_message).pack(side=tk.LEFT)

        self.connections_tree.bind("<<TreeviewSelect>>", self.update_recipient_label)

    def start_node(self):
        self.node = P2PNode(self.host, self.port, self.update_history, self.update_connections_list)
        self.node.start_server()

    def update_history(self, message):
        self.history.configure(state='normal')
        self.history.insert(tk.END, message)
        self.history.configure(state='disabled')
        self.history.see(tk.END)

    def update_connections_list(self):
        for row in self.connections_tree.get_children():
            self.connections_tree.delete(row)
        for connection in self.node.connections:
            self.connections_tree.insert("", "end",
                                         values=(connection['address'][0], connection['address'][1]),
                                         iid=connection['id'])
        self.update_recipient_label()

    def connect_to_peer(self):
        ip = self.ip_entry.get()
        try:
            port = int(self.port_entry.get())
            self.node.connect_to_peer(ip, port)
            self.update_connections_list()
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный номер порта")

    def send_message(self):
        message = self.message_entry.get()
        if message:
            selected = self.connections_tree.selection()
            targets = [conn for conn in self.node.connections if conn['id'] in selected]

            if not targets:
                if not messagebox.askyesno("Подтверждение", "Отправить сообщение всем подключенным?"):
                    return
                targets = None

            self.node.send_text(f"{self.host}:{self.port}: {message}", targets)
            self.update_history(f"Отправлено: {message}\n")
            self.message_entry.delete(0, tk.END)

    def select_file(self):
        self.selected_file = filedialog.askopenfilename()
        if self.selected_file:
            self.update_history(f"Выбран файл: {self.selected_file}\n")

    def send_file(self):
        if self.selected_file:
            selected = self.connections_tree.selection()
            targets = [conn for conn in self.node.connections if conn['id'] in selected]

            if not targets:
                if not messagebox.askyesno("Подтверждение", "Отправить файл всем подключенным?"):
                    return
                targets = None

            self.node.send_file(self.selected_file, targets)
            self.selected_file = None

    def close_selected_connection(self):
        selected = self.connections_tree.selection()
        if selected:
            for connection_id in selected:
                if not self.node.close_connection(connection_id):
                    messagebox.showerror("Ошибка", f"Не удалось закрыть соединение {connection_id}")
            self.update_connections_list()

    def update_recipient_label(self, event=None):
        selected = self.connections_tree.selection()
        if selected:
            recipients = ", ".join(selected)
            self.recipient_label.config(text=recipients)
        else:
            self.recipient_label.config(text="Все")


if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUI(root)
    root.mainloop()