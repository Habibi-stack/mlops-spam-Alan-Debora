"""Script de verificacao de saude e alerta simples (Slides 39 e 40 da Aula 06)."""

import json
import os
import sys
import time
import urllib.request

BASE_URL = os.getenv(
    "API_URL",
    sys.argv[1] if len(sys.argv) > 1 else "https://mlops-spam-alan-debora-1.onrender.com",
)


def checar_saude():
    """Consulta o endpoint /health."""
    url = f"{BASE_URL.rstrip('/')}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Monitor/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True, json.loads(response.read().decode())
            return False, f"HTTP {response.status}"
    except Exception as exc:
        return False, str(exc)


def checar_metricas():
    """Consulta o endpoint /metrics."""
    url = f"{BASE_URL.rstrip('/')}/metrics"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Monitor/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True, json.loads(response.read().decode())
            return False, f"HTTP {response.status}"
    except Exception as exc:
        return False, str(exc)


def executar_monitoramento(intervalo_segundos=10, max_verificacoes=None):
    """Loop de monitoramento com alertas para servico fora do ar, erros ou latencia alta."""
    print("=" * 65)
    print(f"  Monitor de Saude e Alertas — MLOps Observabilidade")
    print(f"  Alvo: {BASE_URL}")
    print(f"  Intervalo: {intervalo_segundos}s")
    print("=" * 65)

    contador = 0
    falhas_consecutivas = 0

    while True:
        contador += 1
        hora = time.strftime("%H:%M:%S")
        ok_saude, res_saude = checar_saude()

        if ok_saude:
            falhas_consecutivas = 0
            ok_metricas, res_metricas = checar_metricas()
            detalhes = ""
            alertas = []

            if ok_metricas:
                reqs = res_metricas.get("requisicoes", 0)
                erros = res_metricas.get("erros_5xx", 0)
                lat = res_metricas.get("latencia_media_ms", 0.0)
                detalhes = f"| Requisicoes: {reqs} | Erros 5xx: {erros} | Latencia: {lat}ms"

                # Alertas baseados nos limites do Slide 39
                if erros > 5:
                    alertas.append(f"ALERTA: Muitos erros 5xx detectados ({erros})")
                if lat > 500.0:
                    alertas.append(f"ALERTA: Latencia media alta ({lat}ms > 500ms)")

            versao = res_saude.get("versao", "?")
            amb = res_saude.get("ambiente", "?")
            print(f"[{hora}] OK - Servico no ar ({versao}, amb: {amb}) {detalhes}")

            for alerta in alertas:
                print(f"[{hora}] >>> {alerta}")
        else:
            falhas_consecutivas += 1
            print(f"[{hora}] ALERTA: servico fora do ar! ({res_saude}) [Falhas: {falhas_consecutivas}]")
            if falhas_consecutivas >= 3:
                print(f"[{hora}] >>> CRITICO: Servico fora do ar 3 vezes seguidas!")

        if max_verificacoes and contador >= max_verificacoes:
            break

        time.sleep(intervalo_segundos)


if __name__ == "__main__":
    executar_monitoramento()
