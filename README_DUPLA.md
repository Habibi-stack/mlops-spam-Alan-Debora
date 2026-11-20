# Classificador de spam — MLOps e Deploy

## O que foi construído

API em FastAPI com os endpoints `/health` e `/predict` e uma página web HTML, CSS e JavaScript servida pela própria API. O modelo TF-IDF + Regressão Logística já treinado é carregado uma vez ao iniciar o serviço.

### Escolhas técnicas

- **FastAPI:** gera documentação Swagger automaticamente e valida o corpo das requisições.
- **Uvicorn:** servidor ASGI simples para desenvolvimento e publicação.
- **HTML/CSS/JavaScript:** página leve, sem framework, sem chave API embutida e sem necessidade de outro serviço.
- **Página no mesmo domínio:** evita problemas de CORS, pois página e API são servidas pela mesma aplicação.
- **Variáveis de ambiente:** permitem trocar versão, ambiente e chave sem alterar o código.

## Pré-requisitos

- Python 3.11 ou 3.12 recomendado
- scikit-learn 1.8.0 exatamente
- Git

## Como executar localmente

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Acesse:

- Página: http://127.0.0.1:8000/
- Documentação: http://127.0.0.1:8000/docs
- Saúde: http://127.0.0.1:8000/health

## Variáveis de ambiente

| Variável | Obrigatória | Uso |
|---|---|---|
| `MODEL_VERSION` | Não; padrão `v1` | Versão exibida no `/health` e `/predict` |
| `APP_ENV` | Não; padrão `dev` | Ambiente exibido pelo `/health` |
| `API_KEY` | Não | Quando definida, protege o `/predict` |
| `MODEL_PATH` | Não | Caminho opcional do arquivo `.joblib` |

Exemplo local:

```text
APP_ENV=dev
MODEL_VERSION=v1
API_KEY=chave-ficticia-123
```

Em produção, use `APP_ENV=test` e configure as variáveis no painel da plataforma de hospedagem. Não coloque a chave real no código ou no repositório.

## Contrato da API

### Saúde

```text
GET /health
```

Resposta:

```json
{"status":"ok","versao":"v1","ambiente":"dev"}
```

### Predição

```text
POST /predict
X-API-Key: chave-ficticia-123
Content-Type: application/json

{"texto":"Parabéns! Você ganhou um prêmio, clique no link"}
```

Resposta:

```json
{"rotulo":"spam","probabilidade":0.67,"versao":"v1"}
```

Texto vazio retorna 422. Sem a chave correta quando `API_KEY` está definida, retorna 401.

## Testes rápidos

Com PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health

$body = @{ texto = "Parabéns! Você ganhou um prêmio, clique no link" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -Headers @{ "X-API-Key" = "chave-ficticia-123" } -ContentType "application/json" -Body $body
```

## Testes Automatizados (QA)

Executar os testes automatizados da API com `pytest`:

```powershell
pip install -r requirements-dev.txt
pytest -v
```

Os testes cobrem:
- `GET /health`: disponibilidade e integridade do contrato.
- `POST /predict`: inferência com dados válidos e checagem de schema da resposta.
- `POST /predict`: validação de segurança com `X-API-Key` (401 quando ausente ou inválida).
- `POST /predict`: validação de payload (422 quando texto vazio ou em branco).
- `GET /`: carregamento da interface web estática.
- Pipeline de CI configurado em `.github/workflows/ci.yml` para execução a cada push/PR.


## Publicação

Publicar como serviço Web no Render apontando para o repositório GitHub. Render foi escolhido por oferecer hospedagem gratuita de API Python, deploy a partir do GitHub e configuração de variáveis de ambiente no painel. O plano gratuito pode hibernar e a primeira requisição pode demorar.

Comando de inicialização no provedor:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configure no provedor:

```text
APP_ENV=test
MODEL_VERSION=v1
API_KEY=<chave fictícia criada no painel>
```

Use o mesmo valor de `API_KEY` apenas no campo da página web durante os testes. Nunca inclua a chave no JavaScript ou no repositório.

URL pública: https://mlops-spam-alan-debora-1.onrender.com

## Organização dos integrantes

- **Alan Lucas Correa de Castro** — [`Habibi-stack`](https://github.com/Habibi-stack) — API, modelo e publicação.
- **Débora Batista** — [`deborabatista1409`](https://github.com/deborabatista1409) — página web, documentação e testes.

## URL pública em Produção

A aplicação está disponível e acessível publicamente em:

```text
https://mlops-spam-alan-debora-1.onrender.com
```

- **Interface Web:** https://mlops-spam-alan-debora-1.onrender.com/
- **Saúde (Healthcheck):** https://mlops-spam-alan-debora-1.onrender.com/health
- **Documentação Swagger:** https://mlops-spam-alan-debora-1.onrender.com/docs


