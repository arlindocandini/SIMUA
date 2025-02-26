import cv2
import os
import time
import base64
import requests
import shutil
import random
from datetime import datetime

# Configuração das pastas
input_folder = 'static/imgGrande'
output_folder = 'static/capturas'
final_folder = 'static/Pasta_final'

# Criar pastas se não existirem
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)
os.makedirs(final_folder, exist_ok=True)

# Configuração da API do ChatGPT
api_key = "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"
api_endpoint = "https://api.openai.com/v1/chat/completions"

# Tamanho da imagem redimensionada
new_width = 300
new_height = 170

# Função para codificar imagem em base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Função para gerar uma localização fictícia
def gerar_localizacao():
    lat = round(random.uniform(-30, -20), 6)
    lon = round(random.uniform(-60, -40), 6)
    return f"{lat}_{lon}"

# Função para gerar um ID único
def gerar_id():
    return f"id{int(time.time() * 1000)}"

# Função para obter a data no formato correto
def obter_data():
    return datetime.now().strftime("%d%m%Y")

# Mapeamento de status
status_map = {
    "buraconaourgente": "buraconaourgente",
    "buracopoucourgente": "buracopoucourgente",
    "buracourgente": "buracourgente",
    "buracoemergencia": "buracoemergencia",
    "bueironaourgente": "bueironaourgente",
    "bueiropoucourgente": "bueiropoucourgente",
    "bueirourgente": "bueirourgente",
    "bueiroemergencia": "bueiroemergencia",
    "fiosoltoemergencia": "fiosoltoemergencia",
    "fiosoltourgente": "fiosoltourgente",
    "fiosoltopoucourgente": "fiosoltopoucourgente",
    "fiosoltonaourgente": "fiosoltonaourgente",
    "matoaltonaourgente" : "matoaltonaourgente",
    "matoaltopoucourgente" : "matoaltopoucourgente",
    "matoaltourgente" : "matoaltourgente",
    "matoaltoemergencia" : "matoaltoemergencia",

}

# Função para classificar imagem com ChatGPT
def classificar_imagem(image_path):
    base64_image = encode_image(image_path)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "Analise a imagem e classifique-a em uma das categorias:  buraco, bueiro, fiosolto, matoalto. Além disso, classifique a urgência como: 'naourgente', 'poucourgente', 'urgente' ou 'emergencia'.  Responda apenas no formato <categoria><urgencia> sem explicações. Analise a imagem atentamente e classifique-a em uma das seguintes categorias: Buraco na pista: Abertura ou depressão no asfalto ou calçada, causada por desgaste, erosão ou falha estrutural. Pode ser grande ou pequeno, mas sempre afeta a superfície. Bueiro aberto: Estrutura de drenagem sem tampa ou danificada. Normalmente tem formato circular ou retangular e é parte de um sistema de escoamento. Mato alto: Vegetação excessiva que pode obstruir a visão ou passagem. Pode estar em calçadas, ruas ou terrenos. Fio solto: Fiação muito baixa podendo oferecer riscos a população Sinalizacao incorreta: Rua com sinalização incorreta, por exemplo: com faixa amarela e branca se misturando ou sinalização apagada Sinaliza faltante: Rua com falta de sinalização, por exemplo: Uma lombada sem placa sinalizando Sem Problemas: Não há risco evidente ou obstrução. Ventilador Copo Se for 'Buraco na pista', 'Mato alto' ou 'Bueiro aberto', classifique a urgência em: Não urgente: Não representa risco imediato. Pouco urgente: Pode piorar, mas não é crítico. Urgente: Necessita atenção em breve. Emergência: Perigo iminente para pedestres ou veículos. IMPORTANTE: Classifique corretamente buracos vs. bueiros: buraco é uma falha no solo/asfalto, bueiro é uma estrutura de drenagem. Responda apenas com o nome da pasta correspondente, sem explicações extras. Exemplos de saída esperada: buracourgente bueirosabertosemergencia matoaltopoucourgente ok"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ],
        "max_tokens": 50
    }

    response = requests.post(api_endpoint, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        resposta = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return status_map.get(resposta, "desconhecido")
    else:
        print(f"Erro na API: {response.status_code} - {response.text}")
        return "erro"

# Função para processar imagens
def processar_imagens():
    for image_name in os.listdir(output_folder):
        image_path = os.path.join(output_folder, image_name)
        if not os.path.isfile(image_path):
            continue

        status = classificar_imagem(image_path)
        if status in ["erro", "desconhecido"]:
            continue

        localizacao = gerar_localizacao()
        id_unico = gerar_id()
        data = obter_data()
        novo_nome = f"{localizacao}__{id_unico}__{status}__{data}.jpg"
        novo_caminho = os.path.join(final_folder, novo_nome)

        shutil.move(image_path, novo_caminho)
        print(f"Imagem {image_name} renomeada e movida para {novo_caminho}")

# Loop para monitoramento
print("Monitorando a pasta 'imgGrande'...")
try:
    while True:
        for image_name in os.listdir(input_folder):
            input_path = os.path.join(input_folder, image_name)
            output_path = os.path.join(output_folder, image_name)

            img = cv2.imread(input_path)
            if img is None:
                continue

            resized_img = cv2.resize(img, (new_width, new_height))
            cv2.imwrite(output_path, resized_img)
            os.remove(input_path)
            print(f"Imagem {image_name} processada para classificação.")

        processar_imagens()
        time.sleep(1)
except KeyboardInterrupt:
    print("Encerrado.")
