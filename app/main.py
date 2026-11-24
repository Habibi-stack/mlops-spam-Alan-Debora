"""API da atividade de classificação de mensagens spam."""

import os
from pathlib import Path

import joblib
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
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

modelo = joblib.load(MODEL_PATH)

app = FastAPI(title="API de classificação de spam")


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok", "versao": MODEL_VERSION, "ambiente": APP_ENV}


@app.post("/predict")
def predict(msg: Mensagem, x_api_key: str | None = Header(default=None)):
    texto = msg.texto.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="O texto não pode estar vazio")

    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente")

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
