from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List
from pathlib import Path

app = FastAPI()

# Add CORS middleware (This is primarily for HTTP requests, but it doesn't hurt to have)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
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

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected")

    async def broadcast(self, message: str):
        print(f"Broadcasting message: {message}")
        for connection in self.active_connections.values():
            await connection.send_text(message)

    def get_active_clients(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        # Notify all clients that a new client has connected
        await manager.broadcast(f"Client {client_id} connected")
        
        while True:
            data = await websocket.receive_text()
            print(f"Message from client {client_id}: {data}")
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # Notify all clients that the client has disconnected
        await manager.broadcast(f"Client {client_id} disconnected")

@app.get("/")
async def get():
    html_content = Path("app/templates/index.html").read_text()
    return HTMLResponse(content=html_content)

@app.get("/clients")
async def get_clients():
    clients = manager.get_active_clients()
    return JSONResponse(content={"clients": clients})

@app.post("/execute")
async def execute_command():
    command = "Hi there"
    await manager.broadcast(command)
    return {"message": "Command sent to all clients"}
