const buscarBtn = document.getElementById("buscar");
const resultado = document.getElementById("resultado");

buscarBtn.addEventListener("click", () => {
  const cidade = document.getElementById("cidade").value.trim();
  const estado = document.getElementById("estado").value.trim();

  if (!cidade || !estado) {
    resultado.innerHTML = `<p class="erro">Preencha cidade e UF.</p>`;
    return;
  }

  resultado.innerHTML = `<div class="loading">🔎 Procurando...</div>`;
  setTimeout(() => buscarCep(cidade, estado), 30);
});

async function buscarCep(cidade, estado) {
  try {
    const r = await fetch("/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cidade, estado })
    });
    const data = await r.json();

    if (data.found) {
      renderCep(data.cep);
    } else {
      renderNaoEncontrado(cidade, estado);
    }
  } catch (e) {
    resultado.innerHTML = `<p class="erro">Erro ao buscar: ${e}</p>`;
  }
}

function renderCep(cep) {
  resultado.innerHTML = `
    <div class="resultado-cep">
      <span>${cep}</span>
      <button id="copiar" class="btn-copiar">📋 Copiar</button>
    </div>
  `;
  ativarCopiar(cep);
}

function renderNaoEncontrado(cidade, estado) {
  resultado.innerHTML = `
    <div class="resultado-cep"><span>CEP não encontrado.</span></div>
    <div class="manual-input">
      <input id="novoCep" placeholder="Digite o CEP (8 dígitos ou com hífen)" maxlength="9">
      <button id="salvarCep" class="btn-salvar">💾 Salvar</button>
    </div>
  `;

  document.getElementById("salvarCep").addEventListener("click", async () => {
    const novoCep = document.getElementById("novoCep").value.trim();
    if (!novoCep) {
      alert("Digite um CEP.");
      return;
    }

    // feedback visual
    const btn = document.getElementById("salvarCep");
    btn.disabled = true;
    btn.textContent = "Salvando...";

    try {
      const r = await fetch("/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cidade, estado, cep: novoCep })
      });
      const data = await r.json();

      if (data.success) {
        // Mostra já como encontrado (cache atualizado)
        renderCep(data.cep || novoCep);
      } else {
        resultado.innerHTML = `<p class="erro">${data.message || "Não foi possível salvar."}</p>`;
      }
    } catch (e) {
      resultado.innerHTML = `<p class="erro">Erro ao salvar: ${e}</p>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "💾 Salvar";
    }
  });
}

function ativarCopiar(valor) {
  const copiarBtn = document.getElementById("copiar");
  copiarBtn.addEventListener("click", async () => {
    copiarBtn.style.transform = "scale(0.92)";
    try {
      await navigator.clipboard.writeText(valor);
      copiarBtn.innerText = "✅ Copiado!";
    } catch {
      copiarBtn.innerText = "✔ Copiado";
    }
    setTimeout(() => {
      copiarBtn.innerText = "📋 Copiar";
      copiarBtn.style.transform = "scale(1)";
    }, 700);
  });
}
