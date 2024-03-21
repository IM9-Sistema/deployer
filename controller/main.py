from datetime import datetime
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from utils import check_signature, ConnectionManager
from notifications import post_discord_webhook
from dotenv import load_dotenv
from auth import create_deployer_session, Deployer, get_deployer_session

load_dotenv('.env')
app = FastAPI()

manager = ConnectionManager()

@app.websocket('/subscribe')
async def subscribe(
	websocket: WebSocket,
	deployer: Deployer = Depends(get_deployer_session)
):
	await manager.connect(websocket)
	try:
		while True:
			data = await websocket.receive_json()
			await manager.broadcast(data|{"origin": deployer.model_dump(mode='json')})
	except WebSocketDisconnect:
		manager.disconnect(websocket)


@app.post("/auth")
async def authenticate(token: str = Depends(create_deployer_session)) -> dict:
	return {
		"detail": "Authenticated",
		"data": token
	}


@app.post("/github")
async def post_event(
	payload: dict,
	x_github_event: Annotated[str, Header()],
	valid: bool = Depends(check_signature),
) -> dict:
	match x_github_event, payload:
		case "ping", _:
			return {"message": "pong"}
		
		case "workflow_run", {"action": "completed", "workflow_run": {"workflow_id": workflow_id, 'conclusion': 'success', 'name': name}}:
			await manager.broadcast({"event": "workflow_run", "data": {"id": workflow_id, "name": name, "concluded": True}})
			return {"message": "OK"}
		
		case "workflow_run", _:
			return {"message": "Ignored (Not in settings, concluded or succeded.)"}
		
		case _:
			raise HTTPException(
				status_code=501,
				detail="Event not supported."
			)