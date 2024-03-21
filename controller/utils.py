import json
from os import environ, listdir, chdir
import subprocess
from typing import Annotated, Any
import hashlib
import hmac
import multiprocessing
from functools import wraps
from notifications import post_discord_webhook
from auth import get_deployer_session
from fastapi import HTTPException, Header, Request, WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_json(message)

def get_secret_key() -> str:
	return environ.get("SECRET_KEY")


def get_discord_webhook_url() -> str:
	return environ.get("DISCORD_WEBHOOK_URL")


# From https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
def verify_signature(payload_body, secret_token, signature_header):
	"""Verify that the payload was sent from GitHub by validating SHA256.

	Raise and return 403 if not authorized.

	Args:
		payload_body: original request body to verify (request.body())
		secret_token: GitHub app webhook token (WEBHOOK_SECRET)
		signature_header: header received from GitHub (x-hub-signature-256)
	"""
	hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
	print(signature_header)
	expected_signature = "sha256=" + hash_object.hexdigest()
	print(expected_signature)
	if not hmac.compare_digest(expected_signature, signature_header):
		raise HTTPException(status_code=403, detail="Request signatures didn't match!")

async def check_signature(request: Request, x_hub_signature_256: Annotated[str, Header()] = None, x_session_key: Annotated[str, Header()] = None) -> bool:
	if x_session_key and get_deployer_session(x_session_key):
		return
	verify_signature(await request.body(), get_secret_key(), x_hub_signature_256 or "")