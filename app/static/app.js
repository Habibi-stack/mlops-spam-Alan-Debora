const message = document.querySelector('#message');
const apiKey = document.querySelector('#apiKey');
const healthBadge = document.querySelector('#healthBadge');
const versionBadge = document.querySelector('#versionBadge');
const envBadge = document.querySelector('#envBadge');
const classifyBtn = document.querySelector('#classifyBtn');
const resultLabel = document.querySelector('#resultLabel');
const resultVersion = document.querySelector('#resultVersion');
const probabilityValue = document.querySelector('#probabilityValue');
const probabilityBar = document.querySelector('#probabilityBar');
const errorBox = document.querySelector('#errorBox');

// Elementos do Painel de Operação
const metricRequests = document.querySelector('#metricRequests');
const metricErrors = document.querySelector('#metricErrors');
const metricLatency = document.querySelector('#metricLatency');
const loadBtn = document.querySelector('#loadBtn');

async function checkHealth() {
  healthBadge.textContent = 'Verificando serviço';
  healthBadge.className = 'badge';
  try {
    const response = await fetch('/health');
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    healthBadge.textContent = 'Serviço OK';
    healthBadge.className = 'badge ok';
    versionBadge.textContent = `versão ${data.versao}`;
    if (envBadge && data.ambiente) {
      envBadge.textContent = `amb: ${data.ambiente}`;
    }
  } catch (error) {
    healthBadge.textContent = 'API fora do ar';
    healthBadge.className = 'badge error';
  }
}

async function fetchMetrics() {
  try {
    const response = await fetch('/metrics');
    if (!response.ok) return;
    const data = await response.json();
    if (metricRequests) metricRequests.textContent = data.requisicoes;
    if (metricErrors) metricErrors.textContent = data.erros_5xx;
    if (metricLatency) metricLatency.textContent = `${data.latencia_media_ms} ms`;
  } catch (_) {}
}

function showError(messageText) {
  errorBox.textContent = messageText;
  errorBox.hidden = false;
}

function clearResult() {
  errorBox.hidden = true;
  errorBox.textContent = '';
}

async function classify() {
  clearResult();
  const chave = apiKey.value.trim();
  if (!chave) {
    showError('A Chave de API é obrigatória. Digite a chave antes de classificar.');
    apiKey.focus();
    return;
  }

  const texto = message.value.trim();
  if (!texto) {
    showError('Erro 422 (Dados inválidos): A mensagem não pode estar vazia.');
    message.focus();
    return;
  }

  classifyBtn.disabled = true;
  classifyBtn.textContent = 'Classificando...';
  try {
    const response = await fetch('/predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': chave
      },
      body: JSON.stringify({ texto })
    });

    if (!response.ok) {
      let detail = `Erro ${response.status}`;
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch (_) {}
      if (response.status === 401) detail = '401 — Chave de API inválida ou ausente.';
      if (response.status === 422) detail = `Erro 422 (Dados inválidos): ${detail}`;
      if (response.status >= 500) detail = 'Erro 500: Erro interno da API.';
      throw new Error(detail);
    }

    const data = await response.json();
    const percentage = data.probabilidade * 100;
    resultLabel.textContent = data.rotulo === 'spam' ? 'spam' : 'não spam';
    resultLabel.className = `result-label ${data.rotulo}`;
    resultVersion.textContent = `respondido pela ${data.versao}`;
    probabilityValue.textContent = `${percentage.toFixed(1)}%`;
    probabilityBar.style.width = `${percentage}%`;
  } catch (error) {
    showError(error.message === 'Failed to fetch' ? 'Não foi possível alcançar a API.' : error.message);
  } finally {
    classifyBtn.disabled = false;
    classifyBtn.textContent = 'Classificar';
    fetchMetrics();
  }
}

document.querySelector('#spamBtn').addEventListener('click', () => {
  message.value = 'Parabéns! Você ganhou um prêmio, clique no link para resgatar agora.';
  message.focus();
});
document.querySelector('#commonBtn').addEventListener('click', () => {
  message.value = 'A reunião de amanhã foi adiada para quinta-feira.';
  message.focus();
});
classifyBtn.addEventListener('click', classify);
message.addEventListener('keydown', (event) => {
  if (event.ctrlKey && event.key === 'Enter') classify();
});

// Botão de Carga: Enviar 50 requisições (Slide 51)
if (loadBtn) {
  loadBtn.addEventListener('click', async () => {
    loadBtn.disabled = true;
    const chave = apiKey.value.trim() || 'chave-ficticia-123';
    const amostras = [
      'Parabéns! Você ganhou um prêmio exclusivo, resgate agora pelo link.',
      'A reunião de alinhamento com a equipe será amanhã às 14h.',
      'URGENTE: Sua conta foi comprometida, clique aqui para atualizar seus dados.',
      'Segue em anexo a planilha de notas da disciplina de MLOps.'
    ];

    const batchSize = 10;
    let completed = 0;
    for (let i = 0; i < 50; i += batchSize) {
      loadBtn.textContent = `Enviando... (${completed}/50)`;
      const promises = [];
      for (let j = 0; j < batchSize && (i + j) < 50; j++) {
        const txt = amostras[(i + j) % amostras.length];
        promises.push(
          fetch('/predict', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': chave
            },
            body: JSON.stringify({ texto: txt })
          }).catch(() => {})
        );
      }
      await Promise.all(promises);
      completed += promises.length;
      await fetchMetrics();
    }

    loadBtn.disabled = false;
    loadBtn.textContent = 'Enviar 50 requisições';
    await fetchMetrics();
  });
}

// Inicialização e polling das métricas
checkHealth();
fetchMetrics();
setInterval(fetchMetrics, 2500);
