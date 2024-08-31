from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List
from pathlib import Path
import json
import hashlib
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the hashed passcode from environment variables
REQUIRED_HASHED_PASSCODE = os.getenv("PASSCODE")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str, passcode: str):
        # Verify passcode
        if not self.verify_passcode(passcode):
            await websocket.close(code=1008, reason="Invalid passcode")
            print(f"Client {client_id} provided an invalid passcode.")
            return None

        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")
        return client_id

    def verify_passcode(self, passcode: str) -> bool:
        # Hash the provided passcode and compare with the stored hash
        hashed_passcode = hashlib.sha256(passcode.encode()).hexdigest()
        return hashed_passcode == REQUIRED_HASHED_PASSCODE

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected")

    async def broadcast(self, message: dict):
        json_message = json.dumps(message)
        print(f"Broadcasting message: {json_message}")
        for connection in self.active_connections.values():
            try:
                await connection.send_text(json_message)
            except Exception as e:
                print(f"Failed to send message to {connection}: {e}")

    def get_active_clients(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, passcode: str):
    connected_client = await manager.connect(websocket, client_id, passcode)
    if not connected_client:
        return
    
    try:
        await manager.broadcast({"type": "status", "client_id": client_id, "status": "connected"})
        
        while True:
            data = await websocket.receive_text()
            print(f"Message from client {client_id}: {data}")
            await websocket.send_text(json.dumps({"type": "echo", "message": data}))
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast({"type": "status", "client_id": client_id, "status": "disconnected"})
        print(f"Client {client_id} disconnected")

@app.get("/")
async def get():
    html_content = Path("app/templates/index.html").read_text()
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
