"""Desktop entry point: start the local service and open the default browser."""

import socket
import threading
import time
import webbrowser

import app


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    port = available_port()
    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=lambda: (time.sleep(0.8), webbrowser.open(url)), daemon=True).start()
    try:
        app.run(host="127.0.0.1", port=port)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
