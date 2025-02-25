from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify
import os
from datetime import datetime
import threading
import time
import subprocess
from classificacao import processar_imagens  # Importa a função de classificação de imagens


app = Flask(__name__)

# Caminho para a pasta com as imagens
IMAGE_FOLDER = os.path.join('static', 'Pasta_final')

# Lista para armazenar as ordens de serviço
ordens_servico = []

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
    data = request.json  # Pegando os dados enviados pelo formulário do popup

    nova_os = {
        'id': len(ordens_servico) + 1,
        'categoria': data['categoria'],
        'status': "Em andamento",  # Sempre começa como "Em andamento"
        'localizacao': data['localizacao'],
        'responsavel': data['responsavel'],
        'prazo': data['prazo'],
        'equipe': data['equipe'],
        'prioridade': data['prioridade'],
        'observacoes': data['observacoes'],
        'data_criacao': datetime.today().strftime('%d/%m/%Y'),
        'data_os': datetime.today().strftime('%d/%m/%Y'),
        'data_prazo': data['prazo']
    }

    ordens_servico.append(nova_os)  # Adicionando a nova OS à lista

    return jsonify({"message": "OS criada com sucesso!", "ordens": ordens_servico})

#@app.route('/gerar_os/<filename>', methods=['POST'])
#def gerar_os(filename):
#    if filename not in ordens_servico:
#        ordens_servico.append(filename)
#    return redirect(url_for('index'))

@app.route('/ordens')
def ordens():
    return render_template('ordens.html', ordens=ordens_servico)


@app.route('/finalizar_os/<int:id>', methods=['POST'])
def finalizar_os(id):
    for os in ordens_servico:
        if os['id'] == id:
            os['status'] = "Finalizada"
            os['data_finalizacao'] = datetime.today().strftime('%d/%m/%Y')
            break
    return jsonify({"message": "OS finalizada com sucesso!"})


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

@app.route('/api/locais')
def api_locais():
    return jsonify(get_image_data())

@app.route('/mapa')
def mapa():
    return render_template('mapa.html')


if __name__ == '__main__':
    app.run(debug=True)
