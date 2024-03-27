
import json
import multiprocessing
from os import chdir, environ, listdir
import socket
import subprocess
from time import sleep
import time
from typing import Any
import uuid

from notifications import post_discord_webhook


def get_actions() -> list[dict[str, Any|str|dict[str, Any|int|str]]]:
	data = []
	for file in listdir("deploys/"):
		if not file.endswith(".json"):
			continue
		with open("deploys/"+file) as f:
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


def get_config() -> dict[str, Any]:
	if "config.json" not in listdir():
		with open("config.json", "w", encoding="utf-8") as f:
			f.write(json.dumps(
				{"id": str(uuid.uuid4()), "name": socket.gethostname(), "project_name": "IM9"}
			))
	with open("config.json", "rb") as f:
		return json.load(f)

def get_discord_webhook_url() -> str:
	return environ.get("DISCORD_WEBHOOK_URL")

def max_size(string: str, size: int) -> str:
	return string[-size:]

def _run_action(action: dict[str, Any|str|dict[str, Any|int|str]], discord_id) -> bool:
	deploy = action['deploy']
	chdir(deploy['path'])
	fields = []
	title = f'`[{action["name"]}]` ⌚ Performando deploy...'
	for id, instruction in enumerate(deploy['commands']):
		content = f'Deploy em execução. `({id+1}/{len(deploy["commands"])})`'
		command = instruction['command']
		field = {
			"name": f"⏳ Etapa `#{id+1}`",
			"value": f"🧑‍💻 `Executando {' '.join(command)}`"
		}
		fields.append(field)

		post_discord_webhook(content, title, fields, id=discord_id)
		process = subprocess.Popen(
			command,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			stdin=subprocess.PIPE,
			shell=instruction['shell'],
			universal_newlines=True
		)
		field['value'] = '⌚ Aguardando `stdout`...'
		post_discord_webhook(content, title, fields, id=discord_id)
		output = ""
		last_update = 0
		while True:
			return_code = process.poll()
			if return_code == None:
				try:				
					output += process.stdout.read(20)
				except UnicodeDecodeError:
					output = "😵 Falha de decodificação (processo em execução - sem stdout)"
				
				if time.time() - last_update > 0.05:
					print('update')
					field['value'] = f'<:im9:1222527177963212830> Em execução\n```{max_size(output, 240)}\n```'
					post_discord_webhook(content, title, fields, id=discord_id)
					last_update = time.time()
				continue
			elif return_code != 0:
				title = f'`[{action["name"]}]` ❌ Deploy falhou.'
				field["name"] = f"❌ Etapa `#{id+1}`"
				field["value"] = f'`❌ {" ".join(command)}`\n```{max_size(process.stderr.read(2046), 240)}```'
				post_discord_webhook(content, title, fields, id=discord_id)
				return
			else:
				field["name"] = f"✅ Etapa `#{id+1}`"
				field["value"] = f'`✅ {" ".join(command)}`'
				post_discord_webhook(content, title, fields, id=discord_id)
				break
	title = f'`[{action["name"]}]` ✅ Deploy concluido com sucesso.'
	post_discord_webhook(' ', title, fields, id=discord_id)

def run_action(action, id):
	multiprocessing.Process(target=_run_action, args=(action,id), daemon=True).start()

