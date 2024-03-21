from datetime import datetime
import json
from multiprocessing import freeze_support
import socket
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException
from dotenv import load_dotenv
from os import environ
import requests
from utils import get_config, get_actions, get_workflows, get_action_by_workflow, run_action
from notifications import post_discord_webhook
from logging import basicConfig, info
load_dotenv('.env')
config = get_config()

def authenticate() -> str:
	config = get_config()
	response = requests.post(
		environ.get("AUTH_URL"), 
		headers={'x-websocket-key': environ.get("WEBSOCKET_KEY")},
		json={
			"id": config['id'],
			"name": config['name'],
			"hostname": socket.gethostname(),
			"project_name": config["project_name"],
			"deploys": get_actions()
		}
	)

	assert response.status_code == 200, "Failed to authenticate"
	return response.json()['data']


def main():
	while True:
		try:
			key = authenticate()
			with connect(environ.get('WEBSOCKET_URL'), additional_headers={'x-session-key': key}) as conn:
				while True:
					data = json.loads(conn.recv())
					
					match data:
						case {"event": "workflow_run", "data": {"id": id, "name": name, "concluded": True}} if id in get_workflows():
							conn.send(json.dumps({"event": "acknowledge", "data": {"workflow_id": id}}))
							action = get_action_by_workflow(id)
							if datetime.now().weekday() == 4:
								post_discord_webhook(f'⚠️ `AVISO`: Uma nova atualização foi enviada hoje (**SEXTA-FEIRA**)', f'`[{action["name"]}]` 🚧 - Atualização detectada.')

							discord_id = post_discord_webhook(f'✅ Workflow `{name}` concluido com status de `sucesso`.\n⌚ Iniciando processo de deploy automático.', f'`[{action["name"]}]` 🚧 - Realizando deploy automático.')

							run_action(action, discord_id)
						case _:
							print(f"Skipped {data}")
							continue

		except WebSocketException:
			# TODO: Notify exception
			continue
		except requests.exceptions.RequestException:
			pass
		except AssertionError:
			# TODO: Notify exception
			continue
		except KeyboardInterrupt:
			return
if __name__ == "__main__":
	freeze_support()
	main()	