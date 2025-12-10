#!/usr/bin/env python3
import socket
import threading
import queue
import time
import sys
import select
import signal

SOCKET_PATH = "/tmp/ipc_pingpong.sock"
RECONNECT_LIMIT = 3
RECONNECT_BASE_DELAY = 1
SHUTDOWN_MESSAGE = "SERVER_SHUTDOWN\n"

class IPCClient:
    def __init__(self, path, reconnect_limit=5, base_delay=0.5):
        self.path = path
        self.reconnect_limit = reconnect_limit
        self.base_delay = base_delay
        self.sock = None
        self.reader_thread = None
        self.out_q = queue.Queue()
        self.stop_event = threading.Event()
        self.connected_event = threading.Event()
        self._lock = threading.Lock()

    def connect(self):
        with self._lock:
            if self.sock:
                return True
            attempt = 0
            while attempt < self.reconnect_limit and not self.stop_event.is_set():
                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.connect(self.path)
                    self.sock = s
                    self.connected_event.set()
                    print(f"Client connected to {self.path}")
                    self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
                    self.reader_thread.start()
                    self._flush_out_queue()
                    return True
                except FileNotFoundError:
                    print(f"Client socket not found at {self.path}, attempt {attempt+1}/{self.reconnect_limit}")
                except ConnectionRefusedError:
                    print(f"Client connection refused, attempt {attempt+1}/{self.reconnect_limit}")
                except Exception as e:
                    print(f"Client connect error: {e}, attempt {attempt+1}/{self.reconnect_limit}")
                attempt += 1
                time.sleep(self.base_delay * (2 ** (attempt-1)))
            print("Client failed to connect after retries")
            self.connected_event.clear()
            return False

    def _flush_out_queue(self):
        while not self.out_q.empty():
            msg = self.out_q.get()
            self._send_raw(msg)

    def _send_raw(self, raw_bytes):
        try:
            self.sock.sendall(raw_bytes)
            return True
        except Exception as e:
            print(f"Client send error: {e}")
            self._handle_disconnect()
            return False

    def send_message(self, text):
        if not text.endswith("\n"):
            text = text + "\n"
        raw = text.encode('utf-8')
        with self._lock:
            if not self.sock:
                print("Client not connected, queuing message and attempting reconnect")
                self.out_q.put(raw)
                self.connect()
            else:
                ok = self._send_raw(raw)
                if not ok:
                    self.out_q.put(raw)
                    self.connect()

    def _reader_loop(self):
        f = self.sock.makefile("rb")
        while not self.stop_event.is_set():
            try:
                line = f.readline()
                if not line:
                    print("Client connection closed by server (EOF)")
                    self._handle_disconnect()
                    return
                text = line.decode('utf-8', errors='replace')
                if text.rstrip("\n") == SHUTDOWN_MESSAGE:
                    print("Client server notified shutdown. Exiting client.")
                    self.stop()
                    return
                print(f"[server reply] {text.rstrip()}")
            except Exception as e:
                print(f"Client reader error: {e}")
                self._handle_disconnect()
                return

    def _handle_disconnect(self):
        with self._lock:
            try:
                if self.sock:
                    self.sock.close()
            except:
                pass
            self.sock = None
            self.connected_event.clear()
        if not self.stop_event.is_set():
            print("Client attempting to reconnect...")
            self.connect()

    def stop(self):
        self.stop_event.set()
        self.connected_event.clear()
        with self._lock:
            try:
                if self.sock:
                    self.sock.close()
            except:
                pass
            self.sock = None
        print("Client stopped")

def main():
    client = IPCClient(SOCKET_PATH, reconnect_limit=RECONNECT_LIMIT, base_delay=RECONNECT_BASE_DELAY)

    def on_sigint(signum, frame):
        print("Client received SIGINT, exiting.")
        client.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)

    client.connect()

    print("Client enter messages in stdin. Ctrl-C to exit.")
    while not client.stop_event.is_set():
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.5)
            if sys.stdin in rlist:
                line = sys.stdin.readline()
                if not line:
                    print("Client stdin closed, exiting.")
                    client.stop()
                    break
                text = line.rstrip("\n")
                if text == "":
                    text = "ping"
                client.send_message(text)
        except KeyboardInterrupt:
            print("Client KeyboardInterrupt")
            client.stop()
            break

if __name__ == "__main__":
    main()

