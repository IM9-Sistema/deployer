from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Header
from utils import check_signature, get_workflows, get_action_by_workflow, run_action
from notifications import post_discord_webhook

app = FastAPI()

@app.post("/github")
async def post_event(
	payload: dict,
	x_github_event: Annotated[str, Header()],
	valid: bool = Depends(check_signature),
) -> dict:
	match x_github_event, payload:
		case "ping", _:
			return {"message": "pong"}
		
		case "workflow_run", {"action": "completed", "workflow_run": {"workflow_id": workflow_id, 'conclusion': 'success', 'name': name}} if workflow_id in get_workflows():
			action = get_action_by_workflow(workflow_id)
			if not action:
				return {"message": "Ignored (Action not found)"} 
			post_discord_webhook(f'✅ Workflow `{name}` concluido com status de `sucesso`.\n⌚ Iniciando processo de deploy automático.', f'`[{action["name"]}]` 🚧 - Realizando deploy automático.')

			run_action(action)
			return {"message": "OK"}
		
		case "workflow_run", _:
			return {"message": "Ignored (Not in settings, concluded or succeded.)"}
		
		case _:
			raise HTTPException(
				status_code=501,
				detail="Event not supported."
			)