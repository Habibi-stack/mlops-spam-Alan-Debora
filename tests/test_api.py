"""Testes automatizados da API do classificador de spam."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, API_KEY

client = TestClient(app)


def test_health_endpoint():
    """Valida se o /health responde 200 e com os campos esperados."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "versao" in data
    assert "ambiente" in data


def test_predict_sucesso():
    """Valida predição com texto válido e API Key correta."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    payload = {"texto": "Parabéns! Você ganhou um prêmio exclusivo, resgate agora!"}

    response = client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["rotulo"] in ["spam", "nao_spam"]
    assert 0.0 <= data["probabilidade"] <= 1.0
    assert "versao" in data


def test_predict_sem_chave_ou_chave_invalida():
    """Se API_KEY estiver configurada, deve retornar 401 para chave ausente ou incorreta."""
    if not API_KEY:
        pytest.skip("API_KEY não configurada no ambiente para teste de autenticação")

    payload = {"texto": "Mensagem qualquer de teste"}

    # Caso A: Sem header X-API-Key
    res_sem_chave = client.post("/predict", json=payload)
    assert res_sem_chave.status_code == 401

    # Caso B: Com header X-API-Key incorreto
    res_chave_errada = client.post("/predict", json=payload, headers={"X-API-Key": "chave-incorreta"})
    assert res_chave_errada.status_code == 401


def test_predict_texto_vazio_deve_falhar():
    """Deve retornar erro 422 quando o texto for vazio ou só conter espaços."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}

    # Caso A: String vazia
    res_vazio = client.post("/predict", json={"texto": ""}, headers=headers)
    assert res_vazio.status_code == 422

    # Caso B: Apenas espaços em branco
    res_espacos = client.post("/predict", json={"texto": "    "}, headers=headers)
    assert res_espacos.status_code == 422


def test_pagina_web_carrega():
    """Valida se a rota raiz (/) entrega a página HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Classificador de spam" in response.text
