"""FastAPI server + WebSocket + scan loop (perangkat aktif saja)."""
import asyncio, json, os, time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

import scanner, local_info

BASE_DIR = Path(__file__).resolve().parent
INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))
PORT     = int(os.getenv("PORT", "8000"))

state = {"devices": [], "subnet": None, "last_scan": None,
         "scanning": False, "error": None}
clients: set = set()


async def broadcast(payload: dict):
    data = json.dumps(payload, default=str)
    dead = []
    for ws in list(clients):
        try:    await ws.send_text(data)
        except Exception: dead.append(ws)
    for ws in dead: clients.discard(ws)


def do_scan():
    try:
        result = scanner.scan_network()
        if "error" in result:
            state["error"] = result["error"]
            return {"type": "error", "error": result["error"]}
        state.update(last_scan=time.time(), devices=result["devices"],
                     subnet=result["subnet"], error=None)
        return {"type": "scan", "devices": result["devices"],
                "subnet": result["subnet"], "scanned_at": state["last_scan"]}
    except Exception as e:
        state["error"] = str(e)
        return {"type": "error", "error": str(e)}


async def run_scan():
    state["scanning"] = True
    await broadcast({"type": "scan_started"})
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, do_scan)
    state["scanning"] = False
    await broadcast(result)


async def scan_loop():
    await asyncio.sleep(1)
    while True:
        await run_scan()
        await asyncio.sleep(INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scan_loop())
    try:    yield
    finally: task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/status")
def status():
    return {
        "local_ip":  local_info.get_local_ip(),
        "public_ip": local_info.get_public_ip(),
        "subnet":    state["subnet"] or scanner.get_local_subnet(),
        "scanning":  state["scanning"],
        "last_scan": state["last_scan"],
        "error":     state["error"],
    }


@app.get("/api/devices")
def devices():
    return {"devices": state["devices"], "subnet": state["subnet"],
            "last_scan": state["last_scan"]}


@app.post("/api/scan")
async def trigger():
    asyncio.create_task(run_scan())
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "init", "devices": state["devices"], "subnet": state["subnet"],
            "scanned_at": state["last_scan"],
        }, default=str))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)


if __name__ == "__main__":
    import uvicorn
    print(f"\n  → http://localhost:{PORT}\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
