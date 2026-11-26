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

## Como executar com Docker

### Opção 1: Via Docker CLI direto

1. Construir a imagem Docker:
```powershell
docker build -t mlops-spam:v1 .
```

2. Executar o contêiner mapeando a porta 8000:
```powershell
docker run -d -p 8000:8000 --name mlops-spam mlops-spam:v1
```

3. Verificar logs e status:
```powershell
docker ps
docker logs mlops-spam
```

4. Parar e remover o contêiner:
```powershell
docker stop mlops-spam
docker rm mlops-spam
```

### Opção 2: Via Docker Compose

Subir a aplicação em segundo plano:
```powershell
docker compose up -d --build
```

Parar a aplicação:
```powershell
docker compose down
```

## Variáveis de ambiente

| Variável | Obrigatória | Uso |
|---|---|---|
| `MODEL_VERSION` | Não; padrão `v1` | Versão exibida no `/health` e `/predict` |
| `APP_ENV` | Não; padrão `dev` | Ambiente exibido pelo `/health` |
| `API_KEY` | Sim (padrão `chave-ficticia-123`) | Protege obrigatoriamente o `/predict` via header `X-API-Key` |
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

Texto vazio retorna 422. Requisições sem a chave correta no cabeçalho `X-API-Key` retornam 401.

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
- `GET /ready`: readiness probe do modelo em memória.
- `GET /metrics`: integridade dos contadores de requisições, erros 5xx e latência.
- `POST /predict`: inferência com dados válidos e checagem de schema da resposta.
- `POST /predict`: validação de segurança com `X-API-Key` (401 quando ausente ou inválida).
- `POST /predict`: validação de payload (422 quando texto vazio ou em branco).
- `GET /`: carregamento da interface web estática com o Painel de Operação.
- Pipeline de CI configurado em `.github/workflows/ci.yml` para execução a cada push/PR.

## Observabilidade (Etapa 4 - Aula 06)

A aplicação conta com observabilidade nativa baseada nos três pilares (Logs, Métricas e Traces simples):

### 1. Logs Estruturados em JSON (stdout)
Cada requisição gera um registro padronizado em JSON na saída padrão (stdout), facilitando a coleta por contêineres e ferramentas de monitoramento:
```json
{"hora": "21:30:05", "nivel": "INFO", "mensagem": "requisicao atendida", "rota": "/predict", "status": 200, "id_req": "d1e2...", "ms": 4.12}
```
* **Privacidade e Segurança:** Chaves de API e textos de mensagens completas nunca são logados (conforme boas práticas do Slide 19).

### 2. Rota `/metrics` (Métricas do Serviço)
Endpoint `GET /metrics` que retorna os contadores do serviço em tempo real:
```json
{
  "requisicoes": 109,
  "erros_5xx": 0,
  "latencia_media_ms": 2.0
}
```

### 3. Painel de Operação na Interface Web
A página inicial (`/`) inclui uma seção de **Painel de Operação** com:
* **Indicadores em tempo real:** Contadores de total de requisições, erros 5xx e latência média em milissegundos.
* **Gerador de carga:** Botão **"Enviar 50 requisições"** para estressar a API e demonstrar a atualização instantânea das métricas e dos logs no contêiner.

### 4. Como inspecionar logs no Docker
Para acompanhar os registros e filtrar incidentes:
```powershell
# Acompanhar logs em tempo real
docker logs -f mlops-spam

# Filtrar apenas erros no PowerShell
docker logs mlops-spam 2>&1 | Select-String "ERROR"
```


## Pipeline CI/CD (Etapa 3 - GitHub Actions)

O projeto possui uma pipeline automatizada de Integração e Entrega Contínua configurada em `.github/workflows/ci.yml`.

### Portões de Qualidade (Quality Gates)

O fluxo é dividido em quatro estágios sequenciais usando a diretiva `needs`, reproduzindo fielmente o modelo do Slide 9 da Aula 04. Cada estágio atua como um portão de qualidade: se a etapa anterior falhar, o pipeline é interrompido imediatamente e o deploy é bloqueado.

1. **Job 1: `Build` (Instala as dependências)**:
   * Executa em ambiente limpo `ubuntu-latest` com Python 3.11.
   * Instala dependências do `requirements.txt` e valida que o projeto compila sem erros de sintaxe (`python -m compileall app/`).
   * **Portão 1:** Se a instalação ou compilação falhar, o pipeline para aqui.

2. **Job 2: `Testes` (pytest e lint)**:
   * Depende de: `needs: build`.
   * Instala dependências de teste e executa a suíte de testes com `pytest -v` (valida endpoints `/health`, `/ready`, `/metrics`, `/predict`, segurança e interface web).
   * **Portão 2:** Se qualquer teste falhar, o empacotamento é bloqueado.

3. **Job 3: `Empacotar` (docker build e push)**:
   * Depende de: `needs: testes`.
   * Constrói a imagem Docker a partir do `Dockerfile`:
     ```bash
     docker build -t spam-service:v1 .
     ```
   * **Portão 3:** Garante que a imagem monta corretamente antes de qualquer tentativa de deploy.

4. **Job 4: `Deploy (teste)` (Publica no ambiente de teste)**:
   * Depende de: `needs: empacotar`.
   * Executado exclusivamente em push na branch `main` ou tags de versão (`v*`).
   * Dispara o webhook do Render (Deploy Hook via segredo `DEPLOY_HOOK_URL`) para atualizar o serviço online.

### Configuração do Deploy Hook (Render -> GitHub Secrets)

1. No painel do **Render**, abra seu Web Service.
2. Acesse **Settings** > **Build & Deploy** > **Deploy Hook**.
3. Copie a URL do Deploy Hook gerada pelo Render (formato: `https://api.render.com/deploy/srv-...`).
4. No repositório do **GitHub**, vá em **Settings** > **Secrets and variables** > **Actions**.
5. Clique em **New repository secret**, nomeie como `DEPLOY_HOOK_URL` e cole a URL copiada.

### Registro de Evidências (Critérios de Aceite)

- **Execução com Sucesso (Verde):** Acompanhe o workflow na aba **Actions** do GitHub. Todos os três jobs (`testes`, `empacotar`, `deploy`) devem finalizar com status verde.
- **Execução com Falha Proposital (Vermelha):**
  1. No arquivo `tests/test_api.py`, altere temporariamente uma asserção (ex: de `assert response.status_code == 200` para `assert response.status_code == 404`).
  2. Faça commit e push.
  3. Na aba **Actions**, observe o job `testes` falhar (vermelho) e confirme que os jobs `empacotar` e `deploy` foram cancelados/bloqueados.
  4. Tire o print/salve o log para comprovação da atuação do portão de qualidade.
  5. Reative o teste correto, faça commit e push para restabelecer o pipeline verde.

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


