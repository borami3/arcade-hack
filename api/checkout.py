import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arcade

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = json.load(open(os.path.join(ROOT, "products.json")))
        try:
            co = arcade.create_checkout([p["productId"] for p in data["bridesmaids"]])
            body = {"checkoutUrl": co["checkoutUrl"], "checkoutId": co["checkoutId"], "live": True}
        except Exception as e:
            print("checkout error, using cached:", e)
            body = {"checkoutUrl": data.get("checkoutUrl"), "checkoutId": data.get("checkoutId"), "live": False}
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
