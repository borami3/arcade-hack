"""Minimal Arcade jewelry API client (stdlib only)."""
import json
import os
import random
import ssl
import time
import urllib.error
import urllib.request
import uuid

BASE = "https://platform.arcade.ai/v1"

try:  # python.org builds on macOS ship without system CA certs
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class ArcadeError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def call(endpoint, body=None, retries=8):
    req = urllib.request.Request(
        f"{BASE}/{endpoint}",
        data=json.dumps(body or {}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['ARCADE_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "match-without-matching/1.0",
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = int(e.headers.get("Retry-After") or 10) + random.uniform(0, 3)
                time.sleep(wait)
                continue
            raise ArcadeError(e.code, e.read().decode(errors="replace")) from None


def request_id():
    return str(uuid.uuid4())


def jewelry_categories():
    return {c["name"]: c for c in call("categories/list")["items"] if c["world"] == "jewelry"}


def create_pattern(prompt, category_id):
    return call("patterns/create", {"requestId": request_id(), "prompt": prompt, "categoryId": category_id})


def wait_for_job(job_id, timeout=600, interval=10, log=print):
    start = time.time()
    while time.time() - start < timeout:
        job = call("jobs/get", {"jobId": job_id})
        if job["status"] in ("succeeded", "failed"):
            return job
        log(f"  job {job_id[:8]} {job['status']} ({int(time.time() - start)}s)")
        time.sleep(interval)
    raise TimeoutError(f"job {job_id} timed out")


def get_product(product_id):
    return call("products/get", {"productId": product_id})


def create_checkout(product_ids):
    return call("checkouts/create", {
        "requestId": request_id(),
        "lines": [{"productId": p, "quantity": 1} for p in product_ids],
        "dropShip": True,
    })
