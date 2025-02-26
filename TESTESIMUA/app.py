import shutil
from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify
import os
from datetime import datetime
import threading
import time
import subprocess
import json  # Importar o módulo json
from classificacao import processar_imagens  # Importa a função de classificação de imagens
import requests


app = Flask(__name__)

# Caminho para a pasta com as imagens
IMAGE_FOLDER = os.path.join('static', 'Pasta_final')
PASTA_OS = os.path.join('static', 'OS')

# Caminho para o arquivo JSON que armazena as OS
ORDENS_JSON = 'ordens_servico.json'

# Criar pasta OS se não existir
if not os.path.exists(PASTA_OS):
    os.makedirs(PASTA_OS)

# Função para carregar as OS do arquivo JSON
def carregar_ordens():
    if os.path.exists(ORDENS_JSON):
        with open(ORDENS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Função para salvar as OS no arquivo JSON
def salvar_ordens(ordens):
    with open(ORDENS_JSON, 'w', encoding='utf-8') as f:
        json.dump(ordens, f, ensure_ascii=False, indent=4)

# Carregar as OS ao iniciar o servidor
ordens_servico = carregar_ordens()

# Função para processar o nome do arquivo e extrair informações
def processar_nome_arquivo(nome_arquivo):
    try:
        nome_sem_extensao, _ = os.path.splitext(nome_arquivo)
        partes = nome_sem_extensao.split('__')

        if len(partes) != 4:
            return None  # Arquivo mal formatado

        localizacao, id_completo, status, data = partes
        id_unico = id_completo.replace('id', '')

        categorias_map = {
            "bueiro": "BUEIRO",
            "fiosolto": "FIO SOLTO",
            "buraco": "BURACO NA PISTA",
            "pistaobstruida": "PISTA OBSTRUÍDA",
            "matoalto": "MATO ALTO"
        }

        categoria = "DESCONHECIDO"
        for chave, valor in categorias_map.items():
            if chave in status:
                categoria = valor
                break

        # Definindo status e cores
        status_map = {
            "emergencia": ("Emergência", "#FF4C4C"),
            "urgente": ("Urgente", "#FFD700"),
            "pouco": ("Pouco Urgente", "#4CAF50"),
            "naourg": ("Não Urgente", "#1E90FF")
        }

        status_formatado, cor_status = status_map.get(next((k for k in status_map if k in status), "indefinido"), ("Indefinido", "#808080"))

        return {
            'arquivo': nome_arquivo,
            'localizacao': localizacao.replace('_', ', '),
            'id': id_unico,
            'categoria': categoria,
            'status': status_formatado,
            'cor_status': cor_status,
            'data': f"{data[:2]}/{data[2:4]}/{data[4:]}"
        }
    except ValueError:
        return None

@app.route('/')
def index():
    imagens = os.listdir(IMAGE_FOLDER)
    dados_imagens = [processar_nome_arquivo(img) for img in imagens if processar_nome_arquivo(img)]
    return render_template('index.html', imagens=dados_imagens)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/Pasta_final/<filename>')
def Pasta_final(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/salvar_os', methods=['POST'])
def salvar_os():
    data = request.json  # Pegando os dados do frontend (modal de criação de OS)

    # Mapeamento de categorias para palavras-chave nos nomes dos arquivos
    categorias_map = {
        "BUEIRO": "bueiro",
        "FIO SOLTO": "fiosolto",
        "BURACO NA PISTA": "buraco",
        "PISTA OBSTRUÍDA": "pistaobstruida",
        "MATO ALTO": "matoalto"
    }

    # Obter a palavra-chave correspondente à categoria da OS
    palavra_chave = categorias_map.get(data['categoria'], "").lower()

    # Obter o endereço legível a partir das coordenadas
    lat, lng = map(float, data['localizacao'].split(", "))
    endereco = obter_endereco(lat, lng)

    # Criando a nova ordem de serviço
    nova_os = {
        'id': len(ordens_servico) + 1,
        'categoria': data['categoria'],
        'status': "Em andamento",  # Sempre começa como "Em andamento"
        'localizacao': data['localizacao'],
        'endereco': endereco,  # Adiciona o endereço legível
        'responsavel': data['responsavel'],
        'prazo': data['prazo'],
        'equipe': data['equipe'],
        'prioridade': data['prioridade'],
        'observacoes': data['observacoes'],
        'data_criacao': datetime.today().strftime('%d/%m/%Y'),
        'data_os': datetime.today().strftime('%d/%m/%Y'),
        'data_prazo': data['prazo']
    }

    # Procurando o arquivo na Pasta_final
    arquivo_nome = None
    print(f"Procurando arquivo para a categoria: {data['categoria']} (palavra-chave: {palavra_chave})")
    for arquivo in os.listdir(IMAGE_FOLDER):  
        print(f"Arquivo encontrado: {arquivo}")
        if palavra_chave in arquivo.lower():  # Verifica se a palavra-chave está no nome do arquivo
            arquivo_nome = arquivo
            break
    print(f"Arquivo selecionado: {arquivo_nome}")

    if arquivo_nome:
        caminho_origem = os.path.join(IMAGE_FOLDER, arquivo_nome)
        caminho_destino = os.path.join(PASTA_OS, arquivo_nome)

        try:
            shutil.move(caminho_origem, caminho_destino)  # Move o arquivo para OS
            ordens_servico.append(nova_os)  # Adiciona a OS à lista
            salvar_ordens(ordens_servico)  # Salva as OS no arquivo JSON
            return jsonify({"mensagem": "OS criada e ocorrência movida!", "status": "sucesso"}), 200
        except Exception as e:
            print(f"Erro ao mover arquivo: {str(e)}")
            return jsonify({"mensagem": f"Erro ao mover arquivo: {str(e)}", "status": "erro"}), 500
    else:
        print("Arquivo da ocorrência não encontrado!")
        return jsonify({"mensagem": "Arquivo da ocorrência não encontrado!", "status": "erro"}), 404
@app.route('/ordens')
def ordens():
    return render_template('ordens.html', ordens=ordens_servico)

@app.route('/finalizar_os/<int:id>', methods=['POST'])
def finalizar_os(id):
    for os in ordens_servico:
        if os['id'] == id:
            os['status'] = "Finalizada"
            os['data_finalizacao'] = datetime.today().strftime('%d/%m/%Y')
            salvar_ordens(ordens_servico)  # Salva as OS no JSON
            return jsonify({"message": "OS finalizada com sucesso!"})
    return jsonify({"message": "OS não encontrada!"}), 404


@app.route('/ordens_filtro')
def ordens_filtro():
    status_filtro = request.args.get('status')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    os_detalhes = [processar_nome_arquivo(os) for os in ordens_servico if processar_nome_arquivo(os)]

    if status_filtro:
        os_detalhes = [os for os in os_detalhes if os and os['status'] == status_filtro]
    if data_inicio and data_fim:
        os_detalhes = [os for os in os_detalhes if data_inicio <= os['data'] <= data_fim]

    return render_template('ordens.html', ordens=os_detalhes, status_filtro=status_filtro)

@app.route('/ocorrencias')
def ocorrencias():
    status_filtro = request.args.get('status')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    imagens = os.listdir(IMAGE_FOLDER)
    dados_imagens = [processar_nome_arquivo(img) for img in imagens if processar_nome_arquivo(img)]

    if status_filtro:
        dados_imagens = [img for img in dados_imagens if img and img['status'] == status_filtro]
    if data_inicio and data_fim:
        dados_imagens = [img for img in dados_imagens if data_inicio <= img['data'] <= data_fim]

    return render_template('ocorrencias.html', imagens=dados_imagens, status_filtro=status_filtro)

@app.route('/api/dashboard')
def api_dashboard():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    imagens = os.listdir(IMAGE_FOLDER)
    dados_imagens = [processar_nome_arquivo(img) for img in imagens if processar_nome_arquivo(img)]

    if data_inicio and data_fim:
        dados_imagens = [img for img in dados_imagens if data_inicio <= img['data'] <= data_fim]

    stats = {
        'Emergência': sum(1 for img in dados_imagens if img and img['status'] == 'Emergência'),
        'Urgente': sum(1 for img in dados_imagens if img and img['status'] == 'Urgente'),
        'Pouco Urgente': sum(1 for img in dados_imagens if img and img['status'] == 'Pouco Urgente'),
        'Não Urgente': sum(1 for img in dados_imagens if img and img['status'] == 'Não Urgente'),
        'Total': len([img for img in dados_imagens if img])
    }
    return jsonify(stats)

@app.route('/api/os_dashboard')
def api_os_dashboard():
    # Criando estrutura para armazenar contagens por data
    os_por_data = {}

    for os in ordens_servico:
        data = os['data_os']
        prioridade = os['prioridade']

        if data not in os_por_data:
            os_por_data[data] = {
                'data': data,  # Incluímos a data para referência
                'Alta': 0, 'Média': 0, 'Baixa': 0,
                'Total OS': 0, 'OS Em Andamento': 0, 'OS Finalizadas': 0
            }

        os_por_data[data][prioridade] += 1
        os_por_data[data]['Total OS'] += 1
        if os['status'] == 'Em andamento':
            os_por_data[data]['OS Em Andamento'] += 1
        elif os['status'] == 'Finalizada':
            os_por_data[data]['OS Finalizadas'] += 1

    # Convertendo dicionário em uma lista
    os_detalhes_lista = list(os_por_data.values())

    return jsonify({'os_detalhes': os_detalhes_lista})

@app.route('/api/ocorrencias')
def api_ocorrencias():
    imagens = os.listdir(IMAGE_FOLDER)
    dados_imagens = [processar_nome_arquivo(img) for img in imagens if processar_nome_arquivo(img)]
    
    print("📡 Enviando os seguintes dados de ocorrências:", dados_imagens)  # Log no terminal

    return jsonify([img for img in dados_imagens if img])

# Iniciar classificação de imagens automaticamente
def iniciar_classificacao():
    print("📸 Iniciando classificação automática de imagens...")
    subprocess.Popen(["python", "classificacao.py"])

# Rodar a classificação em uma thread separada
classificacao_thread = threading.Thread(target=iniciar_classificacao, daemon=True)
classificacao_thread.start()

# Função para obter dados das imagens classificadas
def get_image_data():
    imagens = []
    for arquivo in os.listdir(IMAGE_FOLDER):
        if arquivo.endswith(".jpg") or arquivo.endswith(".png"):
            partes = arquivo.split("__")
            if len(partes) == 4:
                localizacao = partes[0].replace("_", ", ")  # Latitude e Longitude
                id_imagem = partes[1]
                categoria = partes[2]
                data = partes[3].split(".")[0]  # Removendo extensão

                imagens.append({
                    "arquivo": arquivo,
                    "localizacao": localizacao,
                    "id": id_imagem,
                    "categoria": categoria,
                    "data": data,
                    "imagem_url": f"/static/Pasta_final/{arquivo}"
                })
    return imagens


def obter_dados_pasta(pasta, tipo):
    dados = []
    if not os.path.exists(pasta):
        return dados

    for arquivo in os.listdir(pasta):
        info = processar_nome_arquivo(arquivo)
        if info:
            lat, lng = map(float, info["localizacao"].split(", "))
            endereco = obter_endereco(lat, lng)  # Obtém o endereço legível
            dados.append({
                "lat": lat,
                "lng": lng,
                "endereco": endereco,  # Adiciona o endereço legível
                "status": info["status"],
                "categoria": info["categoria"],
                "imagem": f"/static/{pasta}/{arquivo}",
                "tipo": tipo
            })
    return dados




@app.route('/api/locais')
def api_locais():
    return jsonify(get_image_data())

@app.route('/mapa')
def mapa():
    return render_template('mapa.html')

@app.route('/api/mapa')
def api_mapa():
    ocorrencias = obter_dados_pasta("static/Pasta_final", "ocorrencia")
    os_geradas = obter_dados_pasta("static/OS", "os-gerada")
    os_finalizadas = []

    for os_item in carregar_ordens():
        if os_item["status"] == "Finalizada":
            lat, lng = map(float, os_item["localizacao"].split(", "))
            endereco = obter_endereco(lat, lng)  # Obtém o endereço legível
            os_finalizadas.append({
                "lat": lat,
                "lng": lng,
                "endereco": endereco,  # Adiciona o endereço legível
                "status": os_item["status"],
                "categoria": os_item["categoria"],
                "imagem": "",  # Adicionar caminho correto se necessário
                "tipo": "os-finalizada"
            })

    return jsonify({
        "ocorrencias": ocorrencias,
        "os_geradas": os_geradas,
        "os_finalizadas": os_finalizadas
    })

    # Pegando dados das ocorrências e OS geradas
    ocorrencias = obter_dados_pasta("static/Pasta_final", "ocorrencia")
    os_geradas = obter_dados_pasta("static/OS", "os-gerada")

    # Pegando OS finalizadas do JSON
    os_finalizadas = []
    for os_item in carregar_ordens():
        if os_item["status"] == "Finalizada":
            lat, lng = map(float, os_item["localizacao"].split(", "))
            os_finalizadas.append({
                "lat": lat,
                "lng": lng,
                "status": os_item["status"],
                "categoria": os_item["categoria"],
                "imagem": "",  # Adicionar caminho correto se necessário
                "tipo": "os-finalizada"
            })

    return jsonify({
        "ocorrencias": ocorrencias,
        "os_geradas": os_geradas,
        "os_finalizadas": os_finalizadas
    })




ORDENS_SERVICO_JSON = "ordens_servico.json"

# Função para carregar as OS do JSON
def carregar_os():
    try:
        with open(ORDENS_SERVICO_JSON, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

@app.route('/api/ordens_servico')
def api_ordens_servico():
    ordens = carregar_ordens()
    return jsonify(ordens)






def obter_endereco(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
    headers = {
        "User-Agent": "YourAppName/1.0 (your@email.com)"  # Substitua por um identificador válido
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            endereco = data.get("display_name", "Endereço não encontrado")
            return endereco
        else:
            return "Erro ao obter endereço"
    except Exception as e:
        return f"Erro: {str(e)}"





# Caminho para o arquivo de cache
CACHE_ENDERECOS_JSON = 'cache_enderecos.json'

# Função para carregar o cache de endereços
def carregar_cache_enderecos():
    if os.path.exists(CACHE_ENDERECOS_JSON):
        with open(CACHE_ENDERECOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Função para salvar o cache de endereços
def salvar_cache_enderecos(cache):
    with open(CACHE_ENDERECOS_JSON, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

# Função para obter o endereço a partir das coordenadas (com cache)
def obter_endereco(lat, lng):
    # Carrega o cache de endereços
    cache = carregar_cache_enderecos()

    # Cria uma chave única para as coordenadas
    chave = f"{lat},{lng}"

    # Verifica se o endereço já está no cache
    if chave in cache:
        print(f"Endereço encontrado no cache para {chave}: {cache[chave]}")
        return cache[chave]

    # Se não estiver no cache, faz a requisição à API
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
    headers = {
        "User-Agent": "YourAppName/1.0 (your@email.com)"  # Substitua por um identificador válido
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            endereco = data.get("display_name", "Endereço não encontrado")

            # Armazena o endereço no cache
            cache[chave] = endereco
            salvar_cache_enderecos(cache)

            print(f"Endereço obtido da API para {chave}: {endereco}")
            return endereco
        else:
            return "Erro ao obter endereço"
    except Exception as e:
        return f"Erro: {str(e)}"




if __name__ == '__main__':
    app.run(debug=True)