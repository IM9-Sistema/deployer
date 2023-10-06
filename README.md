<center>

# Deployer
CD pipeline dinâmico com integração com github e discord através de webhook.

</center>

### Como usar
1. Definir um workflow no github para testar o código
2. Criar um arquivo `.json` em `deployer/settings/` com o seguinte formato:
```json
{
	"workflow_id": 71570015,
	"name": "Frontend",
	"deploy": {
		"path": "/root/front-producao/",
		"commands": [
			{"command": ["git", "pull"], "shell": false},
			{"command": ["/usr/bin/docker-compose", "up", "--build", "-d"], "shell": false}
		]
	}
}
```
3. Vincular o webhook no github.

>⚠️ Não se esqueça de definir a `SECRET_KEY` no .env
