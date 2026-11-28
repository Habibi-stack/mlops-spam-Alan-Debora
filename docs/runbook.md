# Runbook Operacional — Classificador de Spam

Procedimento padrão de verificação, diagnóstico e resposta para o serviço `spam-service` (baseado na Aula 07, Slide 30).

---

## 1. O que verificar primeiro

1. **Saúde e prontidão da API:**
   - `GET /health` → esperado `200` com `{"status": "ok", "versao": "...", "ambiente": "..."}`.
   - `GET /ready` → esperado `200` com `{"status": "pronto"}` (se retornar `503`, o modelo não está carregado).
   - `GET /metrics` → conferir `requisicoes`, `erros_5xx` (alerta se `> 5`) e `latencia_media_ms` (alerta se `> 500 ms`).
2. **Estado dos pods e eventos no Kubernetes:**
   ```powershell
   kubectl get pods -l app=spam-service
   kubectl get events --sort-by=.metadata.creationTimestamp
   ```
3. **Logs recentes do contêiner:**
   ```powershell
   kubectl logs -l app=spam-service --tail=50
   # Se o pod reiniciou, ver logs da execução anterior:
   kubectl logs --previous <nome-do-pod>
   ```

---

## 2. Diagnóstico por estado do Pod

| Estado / Motivo | Causa provável | O que executar | Ação corretiva |
|---|---|---|---|
| `Pending` | Falta de CPU/memória no nó ou agendamento bloqueado | `kubectl describe pod <nome-do-pod>` | Verificar `resources.requests` em `k8s/deployment.yaml` ou liberar recursos no cluster |
| `ImagePullBackOff` | Nome/tag de imagem incorreto ou falha no registry | `kubectl describe pod <nome-do-pod>` | Corrigir a tag da imagem ou reverter com `kubectl rollout undo deployment/spam-service` |
| `CrashLoopBackOff` | Processo da API falhou ao iniciar ou `livenessProbe` falhando | `kubectl logs --previous <nome-do-pod>` e `kubectl describe pod <nome-do-pod>` | Corrigir erro de inicialização, variável de ambiente ou ajustar `initialDelaySeconds` da probe |
| `OOMKilled` | Contêiner ultrapassou `limits.memory` (`256Mi`) | `kubectl describe pod <nome-do-pod>` (seção `Last State`) | Investigar vazamento/pico de memória ou aumentar `resources.limits.memory` |

---

## 3. Ações operacionais padronizadas

### Reinício controlado (sem derrubar todas as réplicas)
```powershell
kubectl rollout restart deployment/spam-service
kubectl rollout status deployment/spam-service
```

### Escalar réplicas
```powershell
kubectl scale deployment spam-service --replicas=3
```

### Atualizar versão e reverter (Rollback)
```powershell
kubectl set image deployment/spam-service api=spam-service:v2
kubectl rollout status deployment/spam-service
kubectl rollout history deployment/spam-service

# Em caso de falha após deploy:
kubectl rollout undo deployment/spam-service
```

### Verificar o CronJob de checagem periódica
```powershell
kubectl get cronjobs
kubectl get jobs
kubectl logs job/<nome-do-job>
```

---

## 4. Automação segura e quando pedir ajuda

Ao usar `scripts/verificar_saude.py --auto-restart`:
- **Teste antes:** valide primeiro com `--dry-run` em ambiente de teste.
- **Limite de reinícios:** o padrão interrompe após `--max-reinicios 2` (com `--cooldown 120` segundos) para evitar laços de reinício.
- **Auditoria:** use `--log-arquivo logs/automacao.jsonl` para registrar cada ação executada.

**Quando acionar outra pessoa / escalonar o incidente:**
1. O script atingir o limite máximo de reinícios e o serviço continuar fora do ar.
2. Ocorrer `OOMKilled` ou `ImagePullBackOff` recorrente após `rollout undo`.
3. `erros_5xx` continuar subindo mesmo com pods em estado `Running` e `Ready`.
