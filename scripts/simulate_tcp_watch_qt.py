import sys
import socket
import threading
import json
import time
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QLabel
)
from datetime import datetime

DEVICE_ID = "DOG1234"
SERVER_IP = "localhost"
SERVER_PORT = 9000
HTTP_ENDPOINT = "http://localhost:8000/upload"
NOTIFY_ENDPOINT = "http://localhost:8000/notify"


class PlutoSimulator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pluto Watch POC Simulator (Qt Edition)")
        self.setGeometry(100, 100, 1200, 600)

        self.tcp_connected = False
        self.sock = None

        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)

        self.watch_log = QTextEdit()
        self.watch_log.setReadOnly(True)

        self.notify_button = QPushButton("Send Notify to B/E")
        self.notify_button.clicked.connect(self.send_notify)

        self.tcp_button = QPushButton("Connect TCP to B/E")
        self.tcp_button.clicked.connect(self.start_tcp_client)

        self.layout_ui()

    def layout_ui(self):
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("📡 Notify & Debug (Backend)"))
        left_layout.addWidget(self.notify_button)
        left_layout.addWidget(self.debug_log)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("🐶 Watch Logs (Client)"))
        right_layout.addWidget(self.tcp_button)
        right_layout.addWidget(self.watch_log)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        self.setLayout(main_layout)

    def log_debug(self, text):
        now = datetime.now()
        timestamp = now.strftime("[%H:%M:%S.") + f"{int(now.microsecond / 1000):03d}]"
        self.debug_log.append(f"{timestamp} {text}")

    def log_watch(self, text):
        now = datetime.now()
        timestamp = now.strftime("[%H:%M:%S.") + f"{int(now.microsecond / 1000):03d}]"
        self.watch_log.append(f"{timestamp} {text}")

    def send_notify(self):
        try:
            self.log_debug("🔔 Sending /notify request...")
            response = requests.post(NOTIFY_ENDPOINT, json={"deviceId": DEVICE_ID})
            self.log_debug(f"✅ Notify sent: {response.status_code} - {response.text}")
        except Exception as e:
            self.log_debug(f"❌ Notify failed: {str(e)}")

    def upload_data_via_http(self):
        payload = {
            "deviceId": DEVICE_ID,
            "barkCount": 2,
            "timestamp": "2025-04-07T15:30:00Z",
            "status_log": ["resting", "walking", "barking"]
        }
        try:
            self.log_watch("📤 Uploading to /upload via HTTP...")
            response = requests.post(HTTP_ENDPOINT, json=payload)
            self.log_watch(f"📝 HTTP Response: {response.status_code} - {response.text}")
            self.log_watch(f"📦 Sent data: {json.dumps(payload)}")
        except Exception as e:
            self.log_debug(f"❌ Upload failed: {str(e)}")

    def start_tcp_client(self):
        if self.tcp_connected:
            self.log_watch("⚠️ TCP client is already connected.")
            return

        def client_thread():
            try:
                self.log_watch(f"📡 Connecting to {SERVER_IP}:{SERVER_PORT} ...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((SERVER_IP, SERVER_PORT))
                self.tcp_connected = True
                self.log_watch("🟢 Connected to TCP server.")

                # ✅ 연결 직후 deviceId 등록 메시지 전송
                register_msg = {
                    "deviceId": DEVICE_ID
                }
                self.sock.sendall((json.dumps(register_msg) + "\n").encode())
                self.log_watch(f"📤 Sent deviceId registration: {DEVICE_ID}")

                while True:
                    recv = self.sock.recv(1024)
                    if not recv:
                        self.log_watch("❌ Connection closed by server.")
                        break
                    msg = recv.decode().strip()
                    # 강제 newline 제거
                    msg = msg.replace("\\n", "").replace("\n", "").strip()
                    self.log_watch(f"📩 Received from server: {msg}")

                    try:
                        parsed = json.loads(msg)
                        if parsed.get("command") == "SYNC_3MIN":
                            self.upload_data_via_http()
                    except json.JSONDecodeError:
                        self.log_watch("⚠️ Invalid JSON received.")
                    time.sleep(0.1)

            except Exception as e:
                self.log_watch(f"❌ TCP Client error: {str(e)}")
                self.tcp_connected = False

        thread = threading.Thread(target=client_thread, daemon=True)
        thread.start()


def run_simulator():
    app = QApplication(sys.argv)
    window = PlutoSimulator()
    window.show()
    sys.exit(app.exec_())

run_simulator()
