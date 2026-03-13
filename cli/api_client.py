"""HTTP client for the Sahayakan API."""

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("SAHAYAKAN_API_URL", "http://localhost:8000")


def _request(method, path, body=None):
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        raise SystemExit(f"Error: {err.get('detail', e.reason)}") from e


def get(path):
    return _request("GET", path)


def post(path, body=None):
    return _request("POST", path, body)


def put(path, body=None):
    return _request("PUT", path, body)
