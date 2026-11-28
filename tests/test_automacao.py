"""Testes unitários para verificação de saúde, alertas e automação segura."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import verificar_saude as vs


class TestVerificacaoEAutomacao(unittest.TestCase):
    def test_avaliar_metricas_gera_alertas_quando_excede_limites(self):
        alertas = vs.avaliar_metricas({"erros_5xx": 8, "latencia_media_ms": 620.5})
        self.assertEqual(len(alertas), 2)
        self.assertIn("erros 5xx", alertas[0])
        self.assertIn("Latencia media alta", alertas[1])

    def test_avaliar_metricas_sem_alertas_dentro_dos_limites(self):
        alertas = vs.avaliar_metricas({"erros_5xx": 0, "latencia_media_ms": 42.0})
        self.assertEqual(alertas, [])

    @patch("scripts.verificar_saude.subprocess.run")
    def test_reiniciar_deployment_dry_run_nao_executa_kubectl(self, mock_run):
        ok, msg = vs.reiniciar_deployment("spam-service", dry_run=True, confirmar=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        mock_run.assert_not_called()

    @patch("scripts.verificar_saude.subprocess.run")
    def test_reiniciar_deployment_cancelado_sem_confirmacao(self, mock_run):
        ok, msg = vs.reiniciar_deployment(
            "spam-service",
            dry_run=False,
            confirmar=True,
            input_fn=lambda _: "n",
        )
        self.assertFalse(ok)
        self.assertIn("cancelado", msg)
        mock_run.assert_not_called()

    @patch("scripts.verificar_saude.time.sleep")
    @patch("scripts.verificar_saude.reiniciar_deployment")
    @patch("scripts.verificar_saude.checar_saude")
    def test_executar_monitoramento_respeita_limite_de_reinicios(
        self, mock_saude, mock_restart, _mock_sleep
    ):
        mock_saude.return_value = (False, "Connection refused")
        mock_restart.return_value = (True, "deployment.apps/spam-service restarted")

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eventos.jsonl"
            vs.executar_monitoramento(
                base_url="http://localhost:8000",
                intervalo_segundos=0,
                max_verificacoes=7,
                falhas_para_reinicio=3,
                auto_restart=True,
                max_reinicios=1,
                cooldown_segundos=0,
                auto_confirmar=True,
                log_arquivo=str(log_path),
            )
            self.assertEqual(mock_restart.call_count, 1)
            eventos = [json.loads(linha)["evento"] for linha in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertIn("reinicio_controlado_executado", eventos)
            self.assertIn("limite_reinicios_atingido", eventos)


if __name__ == "__main__":
    unittest.main()
