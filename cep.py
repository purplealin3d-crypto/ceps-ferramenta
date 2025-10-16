from flask import Flask, render_template, request, jsonify
import pandas as pd
from unidecode import unidecode
import os
import threading

app = Flask(__name__)

# >>> Ajuste aqui se o nome da sua base principal NÃO for "cep.xlsx"
BASE_CEP = "cep.xlsx"         # sua planilha base
BASE_USER = "user_ceps.xlsx"  # onde gravamos os novos CEPs

# Cache em memória para buscas rápidas
df_cache = None
lock = threading.Lock()

def _norm(s):
    return unidecode(str(s).strip().upper())

def carregar_bases(force_reload=False):
    """
    Carrega base e user_base, normaliza e guarda em cache.
    """
    global df_cache

    if df_cache is not None and not force_reload:
        return df_cache

    # Base principal
    if not os.path.exists(BASE_CEP):
        # Base principal obrigatória: levanta erro claro para você ver no log
        raise FileNotFoundError(f"Base principal não encontrada: {os.path.abspath(BASE_CEP)}")

    base = pd.read_excel(BASE_CEP)

    # Base do usuário (se existir)
    if os.path.exists(BASE_USER):
        user = pd.read_excel(BASE_USER)
    else:
        user = pd.DataFrame(columns=["Cidade", "Estado", "CEP"])

    df = pd.concat([base, user], ignore_index=True)

    # Normalização
    if "Cidade" not in df.columns or "Estado" not in df.columns or "CEP" not in df.columns:
        raise ValueError("As colunas esperadas não foram encontradas. Precisamos de: Cidade, Estado, CEP.")

    df["CidadeNorm"] = df["Cidade"].apply(_norm)
    df["EstadoNorm"] = df["Estado"].apply(lambda x: str(x).strip().upper())

    df_cache = df
    return df_cache

# Carrega ao iniciar
try:
    carregar_bases(force_reload=True)
    print("✅ Bases carregadas com sucesso.")
except Exception as e:
    print(f"⚠️ Erro ao carregar bases no início: {e}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar", methods=["POST"])
def buscar():
    try:
        data = request.get_json(force=True)
        cidade = _norm(data.get("cidade", ""))
        estado = str(data.get("estado", "")).strip().upper()

        df = carregar_bases()
        hit = df.loc[(df["CidadeNorm"] == cidade) & (df["EstadoNorm"] == estado)]

        if not hit.empty:
            cep = str(hit.iloc[0]["CEP"])
            return jsonify({"found": True, "cep": cep})
        else:
            return jsonify({"found": False})
    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500

@app.route("/salvar", methods=["POST"])
def salvar():
    """
    Salva no arquivo do usuário (quando possível) e atualiza o cache em memória imediatamente.
    Retorna success True/False e mensagem.
    """
    global df_cache

    try:
        data = request.get_json(force=True)
        cidade_raw = data.get("cidade", "")
        estado_raw = data.get("estado", "")
        cep_raw    = data.get("cep", "")

        cidade = cidade_raw.strip().upper()
        estado = estado_raw.strip().upper()
        cep    = cep_raw.strip()

        if not (cidade and estado and cep):
            return jsonify({"success": False, "message": "Cidade, estado e CEP são obrigatórios."}), 400

        # 1) Atualiza cache em memória imediatamente (sem travar)
        with lock:
            # Monta linha nova como DataFrame
            new_row = pd.DataFrame([{
                "Cidade": cidade,
                "Estado": estado,
                "CEP": cep,
                "CidadeNorm": _norm(cidade),
                "EstadoNorm": estado
            }])

            if df_cache is None:
                carregar_bases(force_reload=True)

            # concat no cache
            df_local = pd.concat([df_cache, new_row], ignore_index=True)
            df_cache = df_local

        # 2) Tenta gravar em disco (pode falhar no Render Free ou se arquivo estiver aberto no Excel)
        try:
            if os.path.exists(BASE_USER):
                df_user = pd.read_excel(BASE_USER)
            else:
                df_user = pd.DataFrame(columns=["Cidade", "Estado", "CEP"])

            df_user.loc[len(df_user)] = [cidade, estado, cep]
            df_user.to_excel(BASE_USER, index=False)
            persisted = True
        except Exception as disk_err:
            # No Render Free, isso pode falhar (disco efêmero) ou se o Excel estiver aberto localmente
            print(f"⚠️ Não foi possível gravar em disco: {disk_err}")
            persisted = False

        msg = "CEP salvo em memória."
        if persisted:
            msg = "CEP salvo com sucesso!"

        return jsonify({"success": True, "message": msg, "cep": cep})
    except Exception as e:
        return jsonify({"success": False, "message": f"Falha ao salvar: {e}"}), 500

if __name__ == "__main__":
    print("🚀 Servidor iniciado — acesse http://127.0.0.1:5000")
    app.run(debug=True)
