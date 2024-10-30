from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import uvicorn
import json
import socket

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")
        return client_id

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected")

    async def broadcast(self, message: dict):
        json_message = json.dumps(message)
        print(f"Broadcasting message: {json_message}")
        for connection in self.active_connections.values():
            await connection.send_text(json_message)

    def get_active_clients(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        await manager.broadcast({"type": "status", "client_id": client_id, "status": "connected"})
        while True:
            data = await websocket.receive_text()
            print(f"Message from client {client_id}: {data}")
            await websocket.send_text(json.dumps({"type": "echo", "message": data}))
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast({"type": "status", "client_id": client_id, "status": "disconnected"})

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/clients")
async def get_clients():
    clients = manager.get_active_clients()
    return JSONResponse(content={"clients": clients})

@app.post("/execute")
async def execute_command(request: Request):
    data = await request.json()
    command = data.get("type", "unknown")
    await manager.broadcast({"type": "command", "command": command})
    return {"message": f"Command '{command}' sent to all clients"}

def get_local_ip():
    try:
        # Create a socket connection to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    host = get_local_ip()
    port = 8000
    print(f"Server running at http://{host}:{port}")
    print(f"WebSocket URL: ws://{host}:{port}/ws/<client_id>")
    uvicorn.run(app, host=host, port=port)
