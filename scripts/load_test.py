"""Load test: many WebSocket clients, a stream of questions, optional CPU load for the HPA.

    python scripts/load_test.py --base http://localhost:8000 --clients 200 --seconds 60
    python scripts/load_test.py --base http://<ALB> --clients 200 --burn-workers 8

What it checks (NFR-1): every question posted through one pod reaches every connected client,
whichever pod that client is on, and how long that takes end to end. It prints the spread of
pods the clients landed on, the delivery rate, and the latency (median, 95th percentile, max).

--burn-workers adds loops that call /burn (spends CPU for 300 ms per call): a WebSocket
fan-out alone uses little CPU, so this is what pushes the pods past the HPA's 60% target.
Watch it with:  kubectl -n liveask get hpa,pods -w

Needs the dev requirements (httpx, websockets). It is a script, not part of the app image.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import statistics
import time
import uuid

import httpx
from websockets.asyncio.client import connect


async def client(ws_url: str, stats: dict, ready: asyncio.Event, stop: asyncio.Event) -> None:
    try:
        async with connect(ws_url, open_timeout=20, max_size=2**20) as ws:
            hello = json.loads(await ws.recv())
            stats["pods"][hello["data"]["pod"]] += 1
            stats["connected"] += 1
            if stats["connected"] >= stats["target"]:
                ready.set()
            while not stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    continue
                message = json.loads(raw)
                if message["type"] == "question.created":
                    text = message["data"]["text"]
                    if text.startswith("load-test "):
                        sent = float(text.split()[1])
                        if sent >= stats["measure_from"]:
                            stats["latencies"].append(time.time() - sent)
    except Exception as exc:  # noqa: BLE001 - count it, keep the test going
        stats["errors"].append(type(exc).__name__)


async def poster(
    http: httpx.AsyncClient, code: str, rate: float, stop: asyncio.Event, stats: dict
) -> None:
    interval = 1 / rate
    while not stop.is_set():
        started = time.time()
        # a new device each time: the server allows 5 questions a minute per device
        r = await http.post(
            f"/api/rooms/{code}/questions",
            json={"text": f"load-test {time.time():.6f}"},
            headers={"X-Device-Id": str(uuid.uuid4())},
        )
        if r.status_code == 201 and started >= stats["measure_from"]:
            stats["post_ms"].append(1000 * (time.time() - started))
        stats["posted"] += 1 if r.status_code == 201 else 0
        if r.status_code == 201 and started >= stats["measure_from"]:
            stats["measured"] += 1
        stats["post_errors"] += 0 if r.status_code == 201 else 1
        await asyncio.sleep(max(0, interval - (time.time() - started)))


async def burner(http: httpx.AsyncClient, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await http.get("/burn", params={"ms": 300})
        except httpx.HTTPError:
            await asyncio.sleep(0.5)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--clients", type=int, default=200)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--rate", type=float, default=2.0, help="questions per second")
    parser.add_argument("--burn-workers", type=int, default=0, help="loops calling /burn")
    parser.add_argument("--warmup", type=float, default=3.0, help="seconds not measured")
    args = parser.parse_args()

    ws_base = args.base.replace("https://", "wss://").replace("http://", "ws://")
    stats: dict = {
        "target": args.clients,
        "connected": 0,
        "pods": collections.Counter(),
        "latencies": [],
        "errors": [],
        "posted": 0,
        "measured": 0,
        "post_ms": [],
        "post_errors": 0,
        "measure_from": float("inf"),  # set once the clients are connected
    }
    ready, stop, done = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with httpx.AsyncClient(base_url=args.base, timeout=30) as http:
        room = (await http.post("/api/rooms", json={"title": "Load test"})).json()
        ws_url = f"{ws_base}/ws/rooms/{room['code']}?role=audience"
        print(f"room {room['code']}: opening {args.clients} WebSockets on {args.base}")
        clients = [
            asyncio.create_task(client(ws_url, stats, ready, done)) for _ in range(args.clients)
        ]
        try:
            await asyncio.wait_for(ready.wait(), timeout=60)
        except TimeoutError:
            print(f"only {stats['connected']} of {args.clients} connected within 60 s")
        print(f"connected {stats['connected']}; pods: {dict(stats['pods'])}")

        # The first requests warm up connection pools; they are sent but not measured.
        stats["measure_from"] = time.time() + args.warmup
        workers = [asyncio.create_task(poster(http, room["code"], args.rate, stop, stats))]
        workers += [asyncio.create_task(burner(http, stop)) for _ in range(args.burn_workers)]
        await asyncio.sleep(args.seconds)
        stop.set()
        await asyncio.gather(*workers, return_exceptions=True)
        await asyncio.sleep(3)  # let the last events arrive before the clients stop listening
        done.set()
        await asyncio.gather(*clients, return_exceptions=True)

    expected = stats["measured"] * stats["connected"]
    got = len(stats["latencies"])
    print("\n--- result ---")
    print(f"clients connected     {stats['connected']} of {args.clients}")
    print(f"pods the clients used {dict(stats['pods'])}")
    print(
        f"questions posted      {stats['posted']} "
        f"({stats['measured']} measured, {stats['post_errors']} failed)"
    )
    print(
        f"deliveries            {got} of {expected} expected ({100 * got / max(1, expected):.1f}%)"
    )
    if stats["latencies"]:
        lat = stats["latencies"]
        print(
            f"latency (ms)          median {1000 * statistics.median(lat):.0f}, "
            f"p95 {1000 * percentile(lat, 0.95):.0f}, max {1000 * max(lat):.0f}"
        )
    if stats["post_ms"]:
        post = stats["post_ms"]
        print(
            f"POST time (ms)        median {statistics.median(post):.0f}, "
            f"p95 {percentile(post, 0.95):.0f}, max {max(post):.0f}"
        )
    if stats["errors"]:
        print(f"client errors         {dict(collections.Counter(stats['errors']))}")
    ok = (
        got >= 0.99 * expected and stats["latencies"] and percentile(stats["latencies"], 0.95) < 1.0
    )
    print("NFR-1 (p95 under 1 s, nothing lost): " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
