# ws_server.py
import asyncio
import json
import time
from pathlib import Path
import websockets

REC_FILE = Path("configs/recommendations.jsonl")
PORT = 8765

clients = set()

async def notify_clients(msg):
    dead = []
    for ws in clients:
        try:
            await ws.send(msg)
        except:
            dead.append(ws)
    for d in dead:
        clients.remove(d)

async def tail_and_broadcast():
    last_pos = 0
    while True:
        if REC_FILE.exists():
            with open(REC_FILE, "r") as fh:
                fh.seek(last_pos)
                lines = fh.readlines()
                if lines:
                    for line in lines:
                        try:
                            json.loads(line)
                            await notify_clients(line)
                        except:
                            continue
                    last_pos = fh.tell()
        await asyncio.sleep(0.5)

async def handler(websocket, path):
    clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    finally:
        clients.remove(websocket)

async def main():
    server = await websockets.serve(handler, "0.0.0.0", PORT)
    print(f"WebSocket server running on ws://0.0.0.0:{PORT}")
    await tail_and_broadcast()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
