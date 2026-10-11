"""Serves the front end and creates a fresh group checkout on demand (keeps the API key server-side).

Usage: python server.py  ->  http://localhost:8000
"""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import arcade

PORT = int(os.environ.get("PORT", 8000))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/.env") or self.path.endswith(".py"):
            return self.send_error(404)
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/checkout":
            return self.send_error(404)
        data = json.load(open("products.json"))
        try:
            co = arcade.create_checkout([p["productId"] for p in data["bridesmaids"]])
            body = {"checkoutUrl": co["checkoutUrl"], "checkoutId": co["checkoutId"], "live": True}
        except Exception as e:  # demo safety net: fall back to the pre-created checkout
            print("checkout error, using cached:", e)
            body = {"checkoutUrl": data.get("checkoutUrl"), "checkoutId": data.get("checkoutId"), "live": False}
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    arcade.load_env()
    print(f"http://localhost:{PORT}")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
