import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory 저장소
device_states = {}
connected_clients = {}  # device_id: writer

from datetime import datetime

def log(msg):
    now = datetime.now()
    timestamp = now.strftime("[%H:%M:%S.") + f"{int(now.microsecond / 1000):03d}]"
    print(f"{timestamp} {msg}")


@app.post("/notify")
async def notify_app_active(request: Request):
    data = await request.json()
    device_id = data.get("deviceId")
    log(f"🔔 /notify called for deviceId={device_id}")
    writer = connected_clients.get(device_id)
    if writer:
        command = '{ "command": "SYNC_3MIN" }\\n'
        log(f"📤 Sending command to {device_id}: {command.strip()}")
        writer.write(command.encode())
        log(f"🕓 waiting for drain() to complete...")
        await writer.drain()
        log(f"✅ drain() complete")
        return {"status": "SYNC requested to wearable"}
    log(f"⚠️ No connected client for deviceId={device_id}")
    return JSONResponse(status_code=404, content={"error": "Wearable not connected"})

@app.post("/upload")
async def upload_data(request: Request):
    data = await request.json()
    device_id = data.get("deviceId")
    log(f"📥 /upload received from {device_id}: {json.dumps(data)}")
    if not device_id:
        log("❌ /upload failed: Missing deviceId")
        return JSONResponse(status_code=400, content={"error": "Missing deviceId"})
    device_states[device_id] = data
    log(f"✅ Data stored for {device_id}")
    return {"status": "Data uploaded"}

@app.get("/status")
async def get_status(deviceId: str):
    log(f"🔍 /status requested for deviceId={deviceId}")
    state = device_states.get(deviceId)
    if not state:
        log(f"⚠️ No state found for {deviceId}")
        return JSONResponse(status_code=404, content={"error": "No data for device"})
    log(f"📤 Returning state for {deviceId}: {json.dumps(state)}")
    return state

# ✅ TCP 서버 로직
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log(f"📡 New TCP connection from {addr}")
    device_id = None

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            log(f"📩 Received TCP message: {message}")
            msg = json.loads(message)
            device_id = msg.get("deviceId")
            if device_id:
                connected_clients[device_id] = writer
                log(f"✅ Device registered: {device_id}")
                writer.write(b'{ "ack": true }\\n')
                await writer.drain()
    except Exception as e:
        log(f"⚠️ Error with connection {addr}: {e}")
    finally:
        if device_id and device_id in connected_clients:
            del connected_clients[device_id]
            log(f"🧹 Device deregistered: {device_id}")
        writer.close()
        await writer.wait_closed()
        log(f"❌ TCP connection closed: {addr}")

# ✅ FastAPI 실행 전 TCP 서버 시작
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(asyncio.start_server(handle_client, "0.0.0.0", 9000))
    log("🚀 TCP Server started on port 9000")

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
