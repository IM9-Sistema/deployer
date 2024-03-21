import json
import requests


def post_discord_webhook(content: str, title: str, fields: list[dict[str, str]] = None, id: int = None) -> None:
	import utils
	url = utils.get_discord_webhook_url()
	payload ={
	"username": "CI/CD",
		"content": None,
		"embeds": [
			{
			"title": title,
			"description": f"{content}",
			"color": None,
			"fields": fields,
			},
		],
		"attachments": []
		}
	print(id)
	if id:
		resp = requests.patch(
			url+"/messages/"+id,
			data=json.dumps(payload),
			headers={"Content-Type": "application/json"}
		)
		return resp.json()['id']

	return requests.post(
		url+"?wait=true",
		data=json.dumps(payload),
		headers={"Content-Type": "application/json"}
	).json()['id']
