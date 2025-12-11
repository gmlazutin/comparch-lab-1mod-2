#!/usr/bin/env python3
import os
import socket
import signal
import tempfile
from pathlib import Path

class PingPongServer:
    def __init__(self):
        self.socket_path = Path(tempfile.mktemp(prefix='lab1mod2_', suffix='.sock'))
        self.server_socket = None
        self.running = False

    def cleanup_socket(self):
        if self.socket_path.exists():
            self.socket_path.unlink()

    def start(self):
        self.cleanup_socket()
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(str(self.socket_path))
        self.server_socket.listen(5)
        os.chmod(self.socket_path, 0o600)
        self.running = True

        try:
            while self.running:
                try:
                    client_socket, _ = self.server_socket.accept()
                except OSError:
                    break
                with client_socket:
                    self.handle_client(client_socket)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def handle_client(self, client_socket: socket.socket):
        client_id = f"client-{client_socket.fileno()}"
        try:
            with client_socket.makefile('rw', encoding='utf-8', newline='') as fileobj:
                data = fileobj.readline()
                if data:
                    print(f"[serverloop] {client_id} says: {data.strip()}")
                    fileobj.write("pong\n")
                    fileobj.flush()
                else:
                    print(f"[serverloop] {client_id} has disconnected")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            print(f"[serverloop] {client_id} connection reset: {e}")
        except Exception as e:
            print(f"[serverloop] {client_id} unexpected error: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.server_socket.close()
        self.cleanup_socket()

def setup_signal_handlers(server: PingPongServer):
    def signal_handler(signum, _):
        print(f"\nGot signal {signum}, shutting down server...")
        server.stop()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    server = PingPongServer()
    setup_signal_handlers(server)
    print(f"Starting server on {server.socket_path.absolute()}...")
    server.start()

if __name__ == "__main__":
    main()
