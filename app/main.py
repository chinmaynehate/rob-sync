from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("New connection added")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("Connection removed")

    async def broadcast(self, message: str):
        print(f"Broadcasting message: {message}")
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# @app.websocket("/ws/{client_id}")
# async def websocket_endpoint(websocket: WebSocket, client_id: str):
#     await manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             print(f"Message from client {client_id}: {data}")
#             await websocket.send_text(f"Message received: {data}")
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#         print(f"Client {client_id} disconnected")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        # Broadcast the client ID to all connected clients
        await manager.broadcast(f"Client {client_id} connected")
        
        while True:
            data = await websocket.receive_text()
            print(f"Message from client {client_id}: {data}")
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client {client_id} disconnected")


@app.get("/")
async def get():
    html_content = Path("app/templates/index.html").read_text()
    return HTMLResponse(content=html_content)

@app.post("/execute")
async def execute_command():
    command = "Hi there"
    await manager.broadcast(command)
    return {"message": "Command sent to all clients"}
