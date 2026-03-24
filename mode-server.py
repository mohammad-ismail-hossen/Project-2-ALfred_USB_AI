#!/usr/bin/env python3
import http.server
import json
import os
import re
import threading
import subprocess

USB_DIR = os.path.dirname(os.path.abspath(__file__))
MODELFILE = os.path.join(USB_DIR, "Modelfile")
OLLAMA = os.path.join(USB_DIR, "bin/linux/ollama")

MODES = {
    "low": {"temperature": "0.4", "num_ctx": "1024", "num_predict": "150"},
    "medium": {"temperature": "0.6", "num_ctx": "1500", "num_predict": "200"},
    "high": {"temperature": "0.8", "num_ctx": "2048", "num_predict": "400"},
}


def detect_current_mode():
    try:
        with open(MODELFILE, "r") as f:
            content = f.read()

        match = re.search(r"PARAMETER temperature (\S+)", content)
        if match:
            temp = match.group(1)
            if temp == "0.4":
                return "low"
            if temp == "0.8":
                return "high"

        return "medium"
    except Exception:
        return "medium"


status = {
    "switching": False,
    "current": detect_current_mode()
}


def apply_mode(mode):
    status["switching"] = True
    params = MODES[mode]

    with open(MODELFILE, "r") as f:
        content = f.read()

    content = re.sub(
        r"PARAMETER temperature \S+",
        f"PARAMETER temperature {params['temperature']}",
        content
    )
    content = re.sub(
        r"PARAMETER num_ctx \S+",
        f"PARAMETER num_ctx {params['num_ctx']}",
        content
    )
    content = re.sub(
        r"PARAMETER num_predict \S+",
        f"PARAMETER num_predict {params['num_predict']}",
        content
    )

    with open(MODELFILE, "w") as f:
        f.write(content)

    status["current"] = mode
    status["switching"] = False

    def shutdown():
        import time
        time.sleep(1)
        subprocess.run(["pkill", "-f", "ollama"])
        subprocess.run(["pkill", "-f", "python3 -m http.server"])
        os.kill(os.getpid(), 9)

    threading.Thread(target=shutdown, daemon=True).start()


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            self.wfile.write(json.dumps(status).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/mode":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            mode = body.get("mode", "medium")
            if mode in MODES:
                threading.Thread(
                    target=apply_mode,
                    args=(mode,),
                    daemon=True
                ).start()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                self.wfile.write(json.dumps({"ok": True}).encode())
                return

            self.send_response(400)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("localhost", 11435), Handler)
    print("Mode server running on port 11435")
    server.serve_forever()