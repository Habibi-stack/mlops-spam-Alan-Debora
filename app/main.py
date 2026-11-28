"""API da atividade de classificação de mensagens spam."""

import hmac
import json
import os
import time
import uuid
from pathlib import Path

import joblib
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Carrega configuração local do arquivo .env. Em produção, usa as variáveis da plataforma.
load_dotenv()

MODEL_VERSION = os.getenv("MODEL_VERSION", "v2")
APP_ENV = os.getenv("APP_ENV", "dev")
API_KEY = os.getenv("API_KEY", "chave-ficticia-123")
MODEL_PATH = Path(
    os.getenv("MODEL_PATH", str(Path(__file__).resolve().parent.parent / "model" / "modelo.joblib"))
)

app = FastAPI(title="API de classificação de spam")

# Métricas em memória para Observabilidade (Slides 25 e 26 da Aula 06)
metricas = {
    "requisicoes": 0,
    "erros_5xx": 0,
    "ms_total": 0.0,
}


def log_evento(nivel: str, mensagem: str, **campos):
    """Gera logs estruturados em formato JSON na saída padrão (stdout) conforme Slide 17."""
    registro = {
        "hora": time.strftime("%H:%M:%S"),
        "nivel": nivel,
        "mensagem": mensagem,
        **campos,
    }
    print(json.dumps(registro, ensure_ascii=False), flush=True)


try:
    modelo = joblib.load(MODEL_PATH)
except Exception as exc:
    modelo = None
    log_evento("ERROR", "falha ao carregar modelo", caminho=str(MODEL_PATH), erro=str(exc))


@app.middleware("http")
async def medir(request: Request, call_next):
    """Middleware para coleta de métricas e log estruturado (Slides 26 e 34)."""
    id_req = str(uuid.uuid4())
    inicio = time.time()
    rota = request.url.path

    metricas["requisicoes"] += 1
    log_evento("INFO", "inicio requisicao", rota=rota, metodo=request.method, id_req=id_req)

    try:
        resposta = await call_next(request)
    except Exception as exc:
        metricas["erros_5xx"] += 1
        duracao_ms = round((time.time() - inicio) * 1000, 2)
        metricas["ms_total"] += duracao_ms
        log_evento("ERROR", "excecao interna do servidor", rota=rota, erro=str(exc), id_req=id_req, ms=duracao_ms)
        raise exc

    duracao_ms = round((time.time() - inicio) * 1000, 2)
    metricas["ms_total"] += duracao_ms

    if resposta.status_code >= 500:
        metricas["erros_5xx"] += 1
        log_evento("ERROR", "resposta 5xx", rota=rota, status=resposta.status_code, id_req=id_req, ms=duracao_ms)
    else:
        log_evento("INFO", "requisicao atendida", rota=rota, status=resposta.status_code, id_req=id_req, ms=duracao_ms)

    resposta.headers["X-Request-ID"] = id_req
    return resposta


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok", "versao": MODEL_VERSION, "ambiente": APP_ENV}


@app.get("/ready")
def ready():
    """Readiness probe: verifica se o modelo está carregado em memória (Slide 37)."""
    if modelo is None:
        raise HTTPException(status_code=503, detail="Modelo nao carregado")
    return {"status": "pronto"}


@app.get("/metrics")
def ver_metricas():
    """Retorna métricas em formato JSON lidas pelo painel de operação (Slide 27)."""
    n = metricas["requisicoes"]
    media = metricas["ms_total"] / n if n else 0.0
    return {
        "requisicoes": n,
        "erros_5xx": metricas["erros_5xx"],
        "latencia_media_ms": round(media, 1),
    }


@app.post("/predict")
def predict(msg: Mensagem, x_api_key: str | None = Header(default=None)):
    texto = msg.texto.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="O texto não pode estar vazio")

    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente")

    if modelo is None:
        raise HTTPException(status_code=503, detail="Modelo nao carregado")

    probabilidades = modelo.predict_proba([texto])[0]
    indice = int(probabilidades.argmax())
    rotulo = str(modelo.classes_[indice])
    probabilidade = round(float(probabilidades[indice]), 4)

    return {
        "rotulo": rotulo,
        "probabilidade": probabilidade,
        "versao": MODEL_VERSION,
    }


static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
