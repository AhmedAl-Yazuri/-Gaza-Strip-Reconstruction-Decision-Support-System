import json
import sys
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OUTPUT_DIR = ROOT_DIR / "output"
MODULE_DIR = ROOT_DIR / "reconstruction_modules"

OUTPUT_DIR.mkdir(exist_ok=True)

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from pipeline_runner import run_reconstruction_pipeline


JOBS = {}


def _run_job(job_id, selected_projects):
    def progress_callback(step, message, percent):
        JOBS[job_id]["step"] = step
        JOBS[job_id]["message"] = message
        JOBS[job_id]["progress"] = percent

    def log_callback(message):
        JOBS[job_id]["logs"].append(message)
        JOBS[job_id]["logs"] = JOBS[job_id]["logs"][-150:]

    result = run_reconstruction_pipeline(
        selected_projects,
        output_dir=str(OUTPUT_DIR),
        progress_callback=progress_callback,
        log_callback=log_callback,
        profile="web_fast",
    )
    JOBS[job_id]["result"] = result
    JOBS[job_id]["status"] = "done" if result.get("success") else "error"
    JOBS[job_id]["message"] = "Run finished." if result.get("success") else result.get("error", "Run failed.")
    JOBS[job_id]["progress"] = 100


class AppHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".jsx": "text/babel; charset=utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            job_id = parse_qs(parsed.query).get("job_id", [None])[0]
            if not job_id or job_id not in JOBS:
                self._send_json({"error": "Unknown job id."}, status=404)
                return
            job = JOBS[job_id]
            self._send_json(
                {
                    "job_id": job_id,
                    "status": job["status"],
                    "step": job.get("step"),
                    "message": job.get("message"),
                    "progress": job.get("progress", 0),
                    "logs": job.get("logs", []),
                    "result": job.get("result"),
                }
            )
            return

        if parsed.path.startswith("/output/"):
            file_path = ROOT_DIR / parsed.path.lstrip("/")
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                return

            self.send_response(200)
            self.send_header("Content-Length", str(file_path.stat().st_size))
            if file_path.suffix == ".html":
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif file_path.suffix == ".png":
                self.send_header("Content-Type", "image/png")
            elif file_path.suffix == ".txt":
                self.send_header("Content-Type", "text/plain; charset=utf-8")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            with open(file_path, "rb") as handle:
                self.wfile.write(handle.read())
            return

        if parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json({"error": "Not found."}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=400)
            return

        selected_projects = payload.get("selected_projects", [])
        if not isinstance(selected_projects, list) or not selected_projects:
            self._send_json({"error": "selected_projects must be a non-empty list."}, status=400)
            return

        job_id = uuid.uuid4().hex
        JOBS[job_id] = {
            "status": "running",
            "step": "queued",
            "message": "Job accepted.",
            "progress": 0,
            "logs": [f"[job:{job_id}] Accepted with {len(selected_projects)} selected sectors."],
            "result": None,
        }
        threading.Thread(target=_run_job, args=(job_id, selected_projects), daemon=True).start()
        self._send_json({"job_id": job_id, "status": "running"})


def main():
    host = "127.0.0.1"
    port = 8080
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"React UI server running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
