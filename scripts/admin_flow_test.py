#!/usr/bin/env python3
import json
import sys
from urllib.request import Request, urlopen


def post_json(url, data):
    req = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urlopen(req, timeout=10).read().decode())


def get(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    return json.loads(urlopen(req, timeout=10).read().decode())


def main():
    base = "http://127.0.0.1:3002"
    email = "admin@smartlight.ru"
    password = "admin"

    try:
        print("Logging in...")
        r = post_json(f"{base}/api/v1/auth/login", {"email": email, "password": password})
        print("Login response:", r)
        access = r["data"]["access_token"] if "data" in r and "access_token" not in r else r.get("access_token") or r.get("data", {}).get("access_token")
        if not access:
            access = r.get("access_token") or r.get("data", {}).get("access_token")
        refresh = r.get("refresh_token") or (r.get("data") or {}).get("refresh_token")

        print("Calling dashboard...")
        d = get(f"{base}/api/v1", access)
        print("Dashboard:", d)

        print("Calling orders list...")
        o = get(f"{base}/api/v1/orders", access)
        print("Orders:", o)

        if refresh:
            print("Refreshing token...")
            nr = post_json(f"{base}/api/v1/auth/refresh", {"refresh_token": refresh})
            print("Refresh response:", nr)

            print("Logging out (invalidate refresh)...")
            try:
                post_json(f"{base}/api/v1/auth/logout", {"refresh_token": refresh})
                print("Logout OK")
            except Exception as e:
                print("Logout error:", e)

    except Exception as exc:
        print("Error:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
