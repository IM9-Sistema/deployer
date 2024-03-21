from os import environ
from random import choices
from string import ascii_letters
from typing import Annotated
from uuid import UUID

from fastapi import Body, Form, HTTPException, Header, Request, WebSocketException, status
from pydantic import BaseModel

sessions = {}
uuids = {}

class DeployCommands(BaseModel):
	command: list[str]
	shell: bool

class DeployInstructions(BaseModel):
	path: str = None
	commands: list[DeployCommands]

class Workflow(BaseModel):
	workflow_id: int
	name: str
	deploy: DeployInstructions


class Deployer(BaseModel):
	id: UUID
	name: str
	origin: str = None
	hostname: str
	project_name: str
	deploys: list[Workflow]


def random_string(length: int = None):
	return "".join(choices(ascii_letters, k=length or 32))


async def create_deployer_session(request: Request,deployer_info: Annotated[Deployer, Body()], x_websocket_key: Annotated[str, Header()]) -> str:
	print(uuids, sessions)
	if x_websocket_key != environ.get('WEBSOCKET_KEY'):
		raise HTTPException(
			status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect websocket key combination."
		)
	if deployer_info.id in uuids:
		sessions.pop(uuids[deployer_info.id])
		uuids.pop(deployer_info.id)
	deployer_info.origin = request.client.host
	token = random_string(128)
	sessions[token] = deployer_info
	uuids[deployer_info.id] = token
	return token

async def get_deployer_session(x_session_key: Annotated[str, Header()]):
	if x_session_key not in sessions:
		raise WebSocketException(
			403,
			"Invalid session key"
		)
	return sessions[x_session_key]