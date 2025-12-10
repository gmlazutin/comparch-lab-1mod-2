#!/usr/bin/env python3
import socket
import os
import signal
import sys

SOCKET_PATH = "/tmp/ping_pong.sock"

shutdown_requested = False
current_conn = None
server_sock = None


def handle_shutdown(signum, frame):
    global shutdown_requested, current_conn
    print("\n[server] Shutdown signal received, finishing up...")
    shutdown_requested = True
    if current_conn is not None:
        try:
            current_conn.sendall(b"SERVER_SHUTDOWN\n")
        except Exception:
            pass


def cleanup_socket_file():
    if os.path.exists(SOCKET_PATH):
        try:
            os.unlink(SOCKET_PATH)
            print(f"[server] Removed existing socket file: {SOCKET_PATH}")
        except Exception as e:
            print(f"[server] Failed to remove socket file: {e}", file=sys.stderr)


def main():
    global shutdown_requested, current_conn, server_sock

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    cleanup_socket_file()

    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        server_sock.bind(SOCKET_PATH)
    except OSError as e:
        print(f"[server] Failed to bind to {SOCKET_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    server_sock.listen(1)
    print(f"[server] Server started. Listening on Unix socket: {SOCKET_PATH}")

    try:
        while not shutdown_requested:
            print("[server] Waiting for a client to connect...")

            try:
                conn, _ = server_sock.accept()
            except OSError:
                if shutdown_requested:
                    break
                continue

            current_conn = conn
            print("[server] Client connected")

            with conn:
                while not shutdown_requested:
                    try:
                        data = conn.recv(1024)
                    except OSError as e:
                        print(f"[server] Error while receiving data: {e}", file=sys.stderr)
                        break

                    if not data:
                        print("[server] Client disconnected")
                        break

                    message = data.decode("utf-8", errors="replace").rstrip("\n")
                    print(f"[server] Received message: {message!r}")

                    try:M
                        conn.sendall(b"pong\n")
                    except Exception as e:
                        print(f"[server] Failed to send response: {e}")
                        break

            current_conn = None

    finally:
        print("[server] Shutting down server...")
        try:
            if server_sock is not None:
                server_sock.close()
        except Exception:
            pass

        cleanup_socket_file()
        print("[server] Server stopped.")


if __name__ == "__main__":
    main()
