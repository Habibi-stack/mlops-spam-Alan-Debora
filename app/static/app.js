const message = document.querySelector('#message');
const apiKey = document.querySelector('#apiKey');
const healthBadge = document.querySelector('#healthBadge');
const versionBadge = document.querySelector('#versionBadge');
const classifyBtn = document.querySelector('#classifyBtn');
const resultLabel = document.querySelector('#resultLabel');
const resultVersion = document.querySelector('#resultVersion');
const probabilityValue = document.querySelector('#probabilityValue');
const probabilityBar = document.querySelector('#probabilityBar');
const errorBox = document.querySelector('#errorBox');

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
  } catch (error) {
    healthBadge.textContent = 'API fora do ar';
    healthBadge.className = 'badge error';
  }
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
  const texto = message.value.trim();
  if (!texto) {
    showError('Digite uma mensagem antes de classificar.');
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
        'X-API-Key': apiKey.value
      },
      body: JSON.stringify({ texto })
    });

    if (!response.ok) {
      let detail = `Erro ${response.status}`;
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch (_) {}
      if (response.status === 401) detail = '401 — chave de API inválida ou ausente.';
      if (response.status >= 500) detail = 'Erro interno da API. Tente novamente.';
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

checkHealth();
