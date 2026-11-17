import json
import random
import re
import unicodedata
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Cargar respuestas una sola vez al iniciar (más eficiente)
def cargar_respuestas():
    try:
        # Ruta relativa al archivo actual para que funcione en cualquier hosting
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base_dir, 'respuestas.json')
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar respuestas.json: {e}")
        return {"reglas": [], "genericas": []}

BASE_DATOS = cargar_respuestas()

def normalizar_texto(texto):
    """Convierte a minúsculas, remueve tildes, signos de puntuación y espacios extras."""
    if not texto:
        return ""
    texto = texto.lower()
    # Eliminar acentos y tildes
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    # Conservar solo letras, números y espacios
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    # Colapsar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/preguntar', methods=['POST'])
def preguntar():
    data = request.get_json(silent=True) or {}
    consulta_bruta = data.get('pregunta', '')
    consulta_norm = normalizar_texto(consulta_bruta)

    if not consulta_norm:
        return jsonify({
            'respuesta': "La tinta se desvanece sin entender tu mensaje...",
            'audio': 'tom_02_que_puedo_preguntar.mp3'
        })

    mejor_regla = None
    max_puntaje = 0

    # Evaluar todas las reglas y encontrar la de mayor relevancia (palabra/frase más larga)
    for regla in BASE_DATOS.get('reglas', []):
        puntaje_regla = 0
        for kw in regla.get('palabras_clave', []):
            kw_norm = normalizar_texto(kw)
            if kw_norm and kw_norm in consulta_norm:
                # El puntaje equivale a la longitud del término coincidente.
                # Una frase más específica pesará más que una palabra suelta.
                puntos = len(kw_norm)
                if puntos > puntaje_regla:
                    puntaje_regla = puntos

        if puntaje_regla > max_puntaje:
            max_puntaje = puntaje_regla
            mejor_regla = regla

    # Si encontramos una regla coincidente con puntaje positivo
    if mejor_regla and max_puntaje > 0:
        return jsonify({
            'respuesta': mejor_regla['respuesta'],
            'audio': mejor_regla.get('audio', 'tom_02_que_puedo_preguntar.mp3')
        })

    # Si no hubo ninguna coincidencia directa, devolver respuesta genérica
    genericas = BASE_DATOS.get('genericas', [])
    if genericas:
        elegida = random.choice(genericas)
        return jsonify({
            'respuesta': elegida['respuesta'],
            'audio': elegida.get('audio', 'tom_02_que_puedo_preguntar.mp3')
        })

    return jsonify({
        'respuesta': "La tinta se desvanece sin entender tu mensaje...",
        'audio': 'tom_02_que_puedo_preguntar.mp3'
    })

if __name__ == '__main__':
    # En desarrollo local: intentar HTTPS (necesario para micrófono en Chrome)
    # Si no tenés pyOpenSSL instalado, arranca en HTTP normal.
    use_ssl = False
    try:
        import OpenSSL  # noqa: F401
        use_ssl = True
    except ImportError:
        print("pyOpenSSL no instalado → arrancando en HTTP (el micrófono puede no funcionar en algunos navegadores).")
        print("Instalá con: pip install pyopenssl")

    if use_ssl:
        # HTTPS local (certificado auto-firmado)
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
