"""Script de verificação de saúde, alertas e reinício controlado (Aulas 06 e 07)."""

import argparse
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = os.getenv(
    "API_URL",
    "https://mlops-spam-alan-debora-1.onrender.com",
)


def _consultar_json(base_url: str, caminho: str, timeout: int = 5):
    """Consulta um endpoint HTTP GET esperando JSON e retorna (ok, dados_ou_erro)."""
    url = f"{base_url.rstrip('/')}{caminho}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Monitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return True, json.loads(response.read().decode("utf-8"))
            return False, f"HTTP {response.status}"
    except Exception as exc:
        return False, str(exc)


def checar_saude(base_url: str = DEFAULT_BASE_URL):
    """Consulta o endpoint /health."""
    return _consultar_json(base_url, "/health")


def checar_prontidao(base_url: str = DEFAULT_BASE_URL):
    """Consulta o endpoint /ready."""
    return _consultar_json(base_url, "/ready")


def checar_metricas(base_url: str = DEFAULT_BASE_URL):
    """Consulta o endpoint /metrics."""
    return _consultar_json(base_url, "/metrics")


def registrar_evento(nivel: str, evento: str, log_arquivo: str | None = None, **campos) -> None:
    """Registra eventos de monitoramento/automação em JSON quando log_arquivo é informado."""
    registro = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "nivel": nivel,
        "evento": evento,
        **campos,
    }
    if log_arquivo:
        caminho = Path(log_arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("a", encoding="utf-8") as arq:
            arq.write(json.dumps(registro, ensure_ascii=False) + "\n")


def reiniciar_deployment(
    deployment: str = "spam-service",
    namespace: str | None = None,
    dry_run: bool = False,
    confirmar: bool = True,
    input_fn=input,
):
    """Executa `kubectl rollout restart` de forma controlada e auditável."""
    cmd = ["kubectl", "rollout", "restart", f"deployment/{deployment}"]
    if namespace:
        cmd.extend(["-n", namespace])

    if confirmar and not dry_run:
        resposta = input_fn(
            f"Confirmar reinício controlado de deployment/{deployment}? [s/N]: "
        ).strip().lower()
        if resposta not in {"s", "sim", "y", "yes"}:
            return False, "Reinício cancelado pelo operador"

    if dry_run:
        return True, f"[DRY-RUN] Comando simulado: {' '.join(cmd)}"

    resultado = subprocess.run(cmd, capture_output=True, text=True, check=False)
    saida = (resultado.stdout or resultado.stderr or "").strip()
    if resultado.returncode == 0:
        return True, saida or "rollout restart executado com sucesso"
    return False, saida or f"kubectl retornou código {resultado.returncode}"


def avaliar_metricas(metricas: dict, erros_max: int = 5, latencia_max_ms: float = 500.0) -> list[str]:
    """Avalia limites de erros 5xx e latência média e retorna lista de alertas."""
    alertas = []
    erros = metricas.get("erros_5xx", 0)
    latencia = metricas.get("latencia_media_ms", 0.0)
    if erros > erros_max:
        alertas.append(f"ALERTA: Muitos erros 5xx detectados ({erros} > {erros_max})")
    if latencia > latencia_max_ms:
        alertas.append(f"ALERTA: Latencia media alta ({latencia}ms > {latencia_max_ms}ms)")
    return alertas


def executar_monitoramento(
    base_url: str = DEFAULT_BASE_URL,
    intervalo_segundos: int = 10,
    max_verificacoes: int | None = None,
    latencia_max_ms: float = 500.0,
    erros_max: int = 5,
    falhas_para_reinicio: int = 3,
    auto_restart: bool = False,
    deployment: str = "spam-service",
    namespace: str | None = None,
    max_reinicios: int = 2,
    cooldown_segundos: int = 120,
    auto_confirmar: bool = False,
    dry_run: bool = False,
    log_arquivo: str | None = None,
):
    """Loop de monitoramento com alertas e reinício controlado opcional (Slide 27 e Slide 31)."""
    print("=" * 65)
    print("  Monitor de Saude, Alertas e Automacao — MLOps Observabilidade")
    print(f"  Alvo: {base_url}")
    print(f"  Intervalo: {intervalo_segundos}s | Auto-restart: {auto_restart}")
    print("=" * 65)

    contador = 0
    falhas_consecutivas = 0
    reinicios_realizados = 0
    ultimo_reinicio_ts = 0.0

    while True:
        contador += 1
        hora = time.strftime("%H:%M:%S")
        ok_saude, res_saude = checar_saude(base_url)

        if ok_saude:
            falhas_consecutivas = 0
            ok_ready, res_ready = checar_prontidao(base_url)
            ok_metricas, res_metricas = checar_metricas(base_url)
            detalhes = ""
            alertas = []

            if not ok_ready:
                alertas.append(f"ALERTA: Servico vivo (/health), mas nao pronto (/ready: {res_ready})")

            if ok_metricas:
                reqs = res_metricas.get("requisicoes", 0)
                erros = res_metricas.get("erros_5xx", 0)
                lat = res_metricas.get("latencia_media_ms", 0.0)
                detalhes = f"| Requisicoes: {reqs} | Erros 5xx: {erros} | Latencia: {lat}ms"
                alertas.extend(avaliar_metricas(res_metricas, erros_max=erros_max, latencia_max_ms=latencia_max_ms))

            versao = res_saude.get("versao", "?")
            amb = res_saude.get("ambiente", "?")
            print(f"[{hora}] OK - Servico no ar ({versao}, amb: {amb}) {detalhes}")

            for alerta in alertas:
                print(f"[{hora}] >>> {alerta}")
                registrar_evento("WARNING", "alerta_metrica_ou_prontidao", log_arquivo, detalhe=alerta, url=base_url)
        else:
            falhas_consecutivas += 1
            print(f"[{hora}] ALERTA: servico fora do ar! ({res_saude}) [Falhas: {falhas_consecutivas}]")
            registrar_evento(
                "ERROR",
                "falha_healthcheck",
                log_arquivo,
                falhas_consecutivas=falhas_consecutivas,
                erro=str(res_saude),
                url=base_url,
            )

            if falhas_consecutivas >= falhas_para_reinicio:
                print(f"[{hora}] >>> CRITICO: Servico fora do ar {falhas_consecutivas} vezes seguidas!")
                if auto_restart:
                    agora = time.time()
                    if reinicios_realizados >= max_reinicios:
                        aviso = (
                            f"Limite maximo de reinicios ({max_reinicios}) atingido. "
                            "Intervencao humana necessaria!"
                        )
                        print(f"[{hora}] >>> AVISO HUMANO: {aviso}")
                        registrar_evento("CRITICAL", "limite_reinicios_atingido", log_arquivo, aviso=aviso)
                    elif ultimo_reinicio_ts and (agora - ultimo_reinicio_ts) < cooldown_segundos:
                        restante = int(cooldown_segundos - (agora - ultimo_reinicio_ts))
                        print(f"[{hora}] >>> AGUARDE: Cooldown ativo ({restante}s restantes) antes de novo reinicio.")
                    else:
                        ok_restart, msg_restart = reiniciar_deployment(
                            deployment=deployment,
                            namespace=namespace,
                            dry_run=dry_run,
                            confirmar=not auto_confirmar,
                        )
                        if ok_restart:
                            reinicios_realizados += 1
                            ultimo_reinicio_ts = agora
                            falhas_consecutivas = 0
                            print(
                                f"[{hora}] >>> ACAO AUTOMATICA ({reinicios_realizados}/{max_reinicios}): "
                                f"Reinicio executado — {msg_restart}. Avise o responsavel pelo plantao."
                            )
                            registrar_evento(
                                "WARNING",
                                "reinicio_controlado_executado",
                                log_arquivo,
                                deployment=deployment,
                                tentativa=reinicios_realizados,
                                detalhe=msg_restart,
                            )
                        else:
                            print(f"[{hora}] >>> FALHA NO REINICIO CONTROLADO: {msg_restart}")
                            registrar_evento(
                                "ERROR",
                                "falha_reinicio_controlado",
                                log_arquivo,
                                deployment=deployment,
                                detalhe=msg_restart,
                            )

        if max_verificacoes and contador >= max_verificacoes:
            break

        time.sleep(intervalo_segundos)


def criar_parser() -> argparse.ArgumentParser:
    """Cria o parser CLI mantendo compatibilidade com URL posicional opcional."""
    parser = argparse.ArgumentParser(description="Monitoramento de saúde, alertas e reinício controlado.")
    parser.add_argument("url_posicional", nargs="?", help="URL base opcional (ex: http://localhost:8000)")
    parser.add_argument("--url", default=None, help="URL base da API")
    parser.add_argument("--intervalo", type=int, default=10, help="Intervalo em segundos entre verificações")
    parser.add_argument("--max-verificacoes", type=int, default=None, help="Encerra após N verificações")
    parser.add_argument("--latencia-max", type=float, default=500.0, help="Limite de latência média (ms)")
    parser.add_argument("--erros-max", type=int, default=5, help="Limite de erros 5xx")
    parser.add_argument("--falhas-para-reinicio", type=int, default=3, help="Falhas seguidas antes de alertar/reiniciar")
    parser.add_argument("--auto-restart", action="store_true", help="Ativa reinício controlado via kubectl")
    parser.add_argument("--deployment", default="spam-service", help="Nome do Deployment Kubernetes")
    parser.add_argument("--namespace", default=None, help="Namespace Kubernetes opcional")
    parser.add_argument("--max-reinicios", type=int, default=2, help="Máximo de reinícios automáticos por execução")
    parser.add_argument("--cooldown", type=int, default=120, help="Intervalo mínimo (s) entre reinícios")
    parser.add_argument("--sim", action="store_true", help="Confirma reinícios sem perguntar no terminal")
    parser.add_argument("--dry-run", action="store_true", help="Simula o kubectl sem alterar o cluster")
    parser.add_argument("--log-arquivo", default=None, help="Arquivo opcional para gravar eventos em JSON")
    return parser


def main() -> None:
    parser = criar_parser()
    args = parser.parse_args()
    alvo = args.url or args.url_posicional or DEFAULT_BASE_URL
    executar_monitoramento(
        base_url=alvo,
        intervalo_segundos=args.intervalo,
        max_verificacoes=args.max_verificacoes,
        latencia_max_ms=args.latencia_max,
        erros_max=args.erros_max,
        falhas_para_reinicio=args.falhas_para_reinicio,
        auto_restart=args.auto_restart,
        deployment=args.deployment,
        namespace=args.namespace,
        max_reinicios=args.max_reinicios,
        cooldown_segundos=args.cooldown,
        auto_confirmar=args.sim,
        dry_run=args.dry_run,
        log_arquivo=args.log_arquivo,
    )


if __name__ == "__main__":
    main()
