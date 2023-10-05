import json
from os import environ, listdir, chdir
import subprocess
from typing import Annotated, Any
import hashlib
import hmac
import multiprocessing
from functools import wraps
from notifications import post_discord_webhook

from fastapi import HTTPException, Header, Request


def get_secret_key() -> str:
	return environ.get("SECRET_KEY")


def get_discord_webhook_url() -> str:
	return environ.get("DISCORD_WEBHOOK_URL")


def get_actions() -> list[dict[str, Any|str|dict[str, Any|int|str]]]:
	data = []
	for file in listdir("settings/"):
		if not file.endswith(".json"):
			continue
		with open("settings/"+file) as f:
			data.append(json.load(f))
	return data


def get_workflows() -> list[int]:
	actions = get_actions()
	return [i["workflow_id"] for i in actions]


def get_action_by_workflow(id: int) -> dict[str, Any|str|dict[str, Any|int|str]]:
	actions = get_actions()
	for action in actions:
		if action["workflow_id"] == id:
			return action



def _run_action(action: dict[str, Any|str|dict[str, Any|int|str]]) -> bool:
	deploy = action['deploy']
	chdir(deploy['path'])
	for id, instruction in enumerate(deploy['commands']):
		command = instruction['command']
		post_discord_webhook(f'⌚ Executando etapa #`{id}` (`{" ".join(command)}`)', f'`[{action["name"]}]` ⌚ Performando deploy...')
		process = subprocess.Popen(
			command,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			stdin=subprocess.PIPE,
			shell=instruction['shell'],
			universal_newlines=True
		)
		while True:
			return_code = process.poll()
			if return_code == None:
				continue
			elif return_code != 0:
				post_discord_webhook(f'❌ Etapa #`{id}` (`{" ".join(command)}`) retornou uma exceção.\n```\n{process.stderr.read()}\n```', f'`[{action["name"]}]` ❌ Falha ao realizar deploy automático.')
				return
			else:
				post_discord_webhook(f'✅ Etapa #`{id}` (`{" ".join(command)}`) executada com sucesso.\n```\n{process.stdout.read()}\n```', f'`[{action["name"]}]` ✅ Etapa concluida.')
				break
	post_discord_webhook(f'✅ Deploy concluido com sucesso e sem erros.', f'`[{action["name"]}]` ✅ Deploy automático concluido.')

def run_action(action):
	multiprocessing.Process(target=_run_action, args=(action,), daemon=True).start()


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

async def check_signature(request: Request, x_hub_signature_256: Annotated[str, Header()]) -> bool:
	verify_signature(await request.body(), get_secret_key(), x_hub_signature_256)