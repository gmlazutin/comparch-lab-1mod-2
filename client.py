#!/usr/bin/env python3
import socket
import argparse
import time
import signal
import sys
from pathlib import Path

class PingPongClient:
    def __init__(self, socket_path: Path, timeout=30):
        self.socket_path = socket_path
        self.client_socket = None
        self.file_obj = None
        self.max_retries = 3
        self.retries_timeout = 1
        self.timeout = timeout

    def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.client_socket.settimeout(self.timeout)
                self.client_socket.connect(str(self.socket_path))
                self.file_obj = self.client_socket.makefile('rw', encoding='utf-8', newline='')
                return True
            except KeyboardInterrupt:
                return False
            except (ConnectionRefusedError, FileNotFoundError, socket.timeout):
                retries += 1
                time.sleep(self.retries_timeout)
        return False

    def stop(self):
        if self.file_obj:
            try:
                self.file_obj.close()
            except Exception:
                pass
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        self.file_obj = None
        self.client_socket = None

def main():
    parser = argparse.ArgumentParser(description="PingPong Unix socket client")
    parser.add_argument(
        "-s", "--socket",
        type=str,
        required=True,
        help="Path to Unix socket file"
    )
    args = parser.parse_args()

    socket_path = Path(args.socket)
    if not socket_path.exists():
        print(f"[client] Socket file not found: {socket_path}")
        return

    client = PingPongClient(socket_path)
    if not client.connect():
        print("[client] Could not connect, exiting!")
        return

    try:
        while True:
            try:
                msg = input("> ")
            except (KeyboardInterrupt, EOFError):
                print("\n[client] Exiting...")
                break
            if not msg:
                continue
            try:
                client.file_obj.write(msg + "\n")
                client.file_obj.flush()
                response = client.file_obj.readline()
                if not response:
                    print("[client] Server has disconnected")
                    break
                print(f"(server) {response.strip()}")
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                print("[client] Lost connection to server, retrying...")
                client.stop()
                if not client.connect():
                    print("[client] Reconnect failed, exiting!")
                    break
                print("[client] Reconnected!")
    except Exception as e:
        print(f"[client] An error has occurred: {e}")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
