import asyncio
import json
import os
import urllib.parse

import requests
import websockets


BASE_HTTP = os.getenv("IOTHUB_HTTP", "http://localhost:8000")
BASE_WS = os.getenv("IOTHUB_WS", "ws://localhost:8000")
USERNAME = os.getenv("IOTHUB_USER")
PASSWORD = os.getenv("IOTHUB_PASS")
DEVICE = os.getenv("IOTHUB_DEVICE", "DEV-001")
METRIC = os.getenv("IOTHUB_METRIC", "").strip() or None


def login_and_get_token() -> str:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Set IOTHUB_USER and IOTHUB_PASS environment variables.")

    resp = requests.post(
        f"{BASE_HTTP}/api/auth/login/",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()

    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Login response has no access_token.")
    return token


def build_ws_url(token: str) -> str:
    params = {"token": token, "device": DEVICE}
    if METRIC:
        params["metric"] = METRIC
    return f"{BASE_WS}/ws/telemetry/stream/?{urllib.parse.urlencode(params)}"


async def listen_forever(ws_url: str):
    retry = 1
    while True:
        try:
            print("Connecting to WS stream...")
            async with websockets.connect(
                ws_url, ping_interval=20, ping_timeout=20, close_timeout=5
            ) as ws:
                print("Connected. Waiting telemetry...")
                retry = 1
                async for msg in ws:
                    try:
                        print(json.dumps(json.loads(msg), ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(msg)
        except Exception as e:
            print(f"WS error: {e}. Reconnect in {retry}s")
            await asyncio.sleep(retry)
            retry = min(retry * 2, 15)


async def main():
    token = login_and_get_token()
    ws_url = build_ws_url(token)
    await listen_forever(ws_url)


if __name__ == "__main__":
    asyncio.run(main())
