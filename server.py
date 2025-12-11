#!/usr/bin/env python3
import os
import socket
import signal
import tempfile
from pathlib import Path
import argparse
from threading import Thread, Lock

class PingPongServer:
    def __init__(self, accept_timeout=1, client_timeout=30, socket_path=None):
        if not socket_path:
            self.socket_path = Path(tempfile.mktemp(prefix='lab1mod2_', suffix='.sock'))
        else:
            self.socket_path = socket_path
        self.server_socket = None
        self.running = False
        self.threads = []
        self.lock = Lock()
        self.accept_timeout = accept_timeout
        self.client_timeout = client_timeout

    def cleanup_socket(self):
        if self.socket_path.exists():
            self.socket_path.unlink()

    def start(self):
        self.cleanup_socket()
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(str(self.socket_path))
        self.server_socket.listen(10)
        os.chmod(self.socket_path, 0o600)
        self.server_socket.settimeout(self.accept_timeout)
        self.running = True

        try:
            while self.running:
                try:
                    client_socket, _ = self.server_socket.accept()
                    client_socket.settimeout(self.client_timeout)
                    thread = Thread(target=self.handle_client_loop, args=(client_socket,), daemon=True)
                    thread.start()
                    self.threads.append(thread)
                except socket.timeout:
                    continue
                except OSError:
                    break
        finally:
            self.stop()

    def handle_client_loop(self, client_socket: socket.socket):
        client_id = f"client-{client_socket.fileno()}"
        with self.lock:
            print(f"[serverloop] {client_id} has connected")
        try:
            with client_socket:
                with client_socket.makefile('rw', encoding='utf-8', newline='') as fileobj:
                    while self.running:
                        try:
                            data = fileobj.readline()
                        except socket.timeout:
                            with self.lock:
                                print(f"[serverloop] {client_id} timed out")
                            break
                        if not data:
                            with self.lock:
                                print(f"[serverloop] {client_id} has disconnected")
                            break
                        with self.lock:
                            print(f"[serverloop] {client_id} says: {data.strip()}")
                        fileobj.write("pong\n")
                        fileobj.flush()
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            with self.lock:
                print(f"[serverloop] {client_id} connection reset: {e}")
        except Exception as e:
            with self.lock:
                print(f"[serverloop] {client_id} unexpected error: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
        self.cleanup_socket()
        for t in self.threads:
            t.join(timeout=1)

def main():
    parser = argparse.ArgumentParser(description="PingPong Unix socket server")
    parser.add_argument(
        "-s", "--socket",
        type=str,
        required=False,
        help="Path to new Unix socket file"
    )
    args = parser.parse_args()

    socket_path = None
    if args.socket:
        try:
            socket_path = Path(args.socket)
        except:
            print("[server] Invalid socket path!")
            return

    server = PingPongServer(socket_path=socket_path)
    print(f"Starting server on {server.socket_path.absolute()}...")
    try:
        try:
            server.start()
        finally:
            server.stop()
    except KeyboardInterrupt:
        print("\n[server] Exiting...")
    except Exception as e:
        print(f"[server] An error has occurred: {e}")

if __name__ == "__main__":
    main()
