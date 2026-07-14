import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re

class IntentClassifier:
    def __init__(self, model_path="core/bert_intent_model"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encuentra el modelo en {model_path}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        with open(f"{model_path}/label_mapping.json", "r", encoding="utf-8") as f:
            mapping = json.load(f)
        self.id2label = {int(k): v for k, v in mapping["id2label"].items()}
        self.label2id = mapping["label2id"]
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        print(f"✅ Modelo BERT cargado desde {model_path}")
        print(f"📊 Intenciones: {list(self.id2label.values())}")
    
    def extraer_entidades(self, texto, intent):
        entidades = {}
        texto_lower = texto.lower()
        
        if intent == "abrir_programa":
            # Diccionarios de programas y correcciones
            programas = {
                'chrome': 'chrome',
                'google chrome': 'chrome',
                'firefox': 'firefox',
                'edge': 'edge',
                'microsoft edge': 'edge',
                'visual studio code': 'vscode',
                'vscode': 'vscode',
                'codigo': 'vscode',
                'editor de codigo': 'vscode',
                'spotify': 'spotify',
                'discord': 'discord',
                'telegram': 'telegram',
                'whatsapp': 'whatsapp',
                'teams': 'teams',
                'zoom': 'zoom',
                'opera': 'opera',
                'brave': 'brave',
                'vlc': 'vlc',
                'reproductor vlc': 'vlc',
                'photoshop': 'photoshop',
                'illustrator': 'illustrator',
                'premiere pro': 'premiere pro',
                'after effects': 'after effects',
                'blender': 'blender',
                'obs': 'obs',
                'word': 'word',
                'microsoft word': 'word',
                'excel': 'excel',
                'microsoft excel': 'excel',
                'calculadora': 'calculadora',
                'explorador': 'explorador',
                'cmd': 'cmd',
                'terminal': 'cmd',
                'consola': 'cmd',
                'notepad': 'notepad',
                'bloc de notas': 'notepad',
                'powerpoint': 'powerpoint'
            }
            correcciones = {
                'crom': 'chrome',
                'crome': 'chrome',
                'chrom': 'chrome',
                'croome': 'chrome',
                'cron': 'chrome',
                'crm': 'chrome',
                'exel': 'excel',
                'word': 'word',
                'visual': 'vscode',
                'code': 'vscode',
                'estudio codigo': 'vscode',
                'estudio de codigo': 'vscode',
                'bloc notas': 'notepad',
                'bloc de notas': 'notepad',
                'notas': 'notepad'
            }
            todos = {**programas, **correcciones}
            
            # Detectar acción: abrir o cerrar
            if any(word in texto_lower for word in ["cerrar", "cierra", "termina", "finaliza", "cierre", "close"]):
                entidades["app_action"] = "close"
            else:
                entidades["app_action"] = "open"
            
            # Buscar nombre de la aplicación
            for key, value in todos.items():
                if key in texto_lower:
                    entidades["app"] = value
                    break
            
            if not entidades.get("app"):
                verbos = ['abre', 'abrir', 'inicia', 'ejecuta', 'lanza', 'arranca', 'quiero', 'necesito']
                palabras = texto_lower.split()
                for p in reversed(palabras):
                    if p not in verbos and len(p) > 2:
                        if p in todos:
                            entidades["app"] = todos[p]
                            break
                        for key in todos:
                            if p in key or key in p:
                                entidades["app"] = todos[key]
                                break
                        if entidades.get("app"):
                            break
            
            if not entidades.get("app"):
                if "navegador" in texto_lower or "internet" in texto_lower:
                    entidades["app"] = "navegador"
                elif "word" in texto_lower:
                    entidades["app"] = "word"
                elif "excel" in texto_lower:
                    entidades["app"] = "excel"
        
        elif intent == "reproducir_audio":
            # Eliminar verbos y palabras comunes
            texto_limpio = texto_lower
            palabras_eliminar = [
                'pon', 'reproduce', 'toca', 'escuchar', 'quiero', 'poner',
                'reproducir', 'musica', 'cancion', 'ponme', 'coloca', 'pasa',
                'de', 'la', 'el', 'los', 'las', 'un', 'una', 'algo', 'una',
                'por', 'favor', 'favor', 'gracias'
            ]
            for palabra in palabras_eliminar:
                patron = r'\b' + re.escape(palabra) + r'\b'
                texto_limpio = re.sub(patron, '', texto_limpio)
            texto_limpio = re.sub(r'[^\w\s]', '', texto_limpio)
            texto_limpio = ' '.join(texto_limpio.split())
            if texto_limpio:
                entidades["query"] = texto_limpio
            else:
                entidades["query"] = ""
        
        elif intent == "buscar_web":
            palabras = texto_lower.split()
            verbos_busqueda = ['busca', 'googlea', 'investiga', 'encuentra', 'buscar', 'busqueda', 'informacion', 'saber']
            for verbo in verbos_busqueda:
                if verbo in palabras:
                    idx = palabras.index(verbo)
                    if idx + 1 < len(palabras):
                        entidades["consulta"] = ' '.join(palabras[idx+1:])
                        break
            if not entidades.get("consulta"):
                entidades["consulta"] = texto_lower
        
        elif intent == "cambiar_volumen":
            numeros = re.findall(r'\d+', texto)
            if numeros:
                entidades["level"] = int(numeros[0])
            elif "minimo" in texto_lower or "mínimo" in texto_lower or "0" in texto_lower:
                entidades["level"] = 0
            elif "silencio" in texto_lower:
                entidades["level"] = 0
        
        return entidades
    
    def classify(self, text):
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=64,
            return_tensors="pt"
        )
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(predictions, dim=-1).item()
            confidence = predictions[0][predicted_class].item()
        
        intent_name = self.id2label[predicted_class]
        print(f"🎯 Intención: {intent_name} ({confidence:.2%})")
        
        intent_map = {
            "abrir_programa": {"type": "action", "action": "open_app"},
            "reproducir_audio": {"type": "action", "action": "music"},
            "buscar_web": {"type": "action", "action": "search_web"},
            "subir_volumen": {"type": "action", "action": "volume_up"},
            "bajar_volumen": {"type": "action", "action": "volume_down"},
            "cambiar_volumen": {"type": "action", "action": "set_volume"},
            "apagar_pc": {"type": "action", "action": "shutdown"},
            "reiniciar_pc": {"type": "action", "action": "restart"},
            "saludo": {"type": "conversation"},
            "despedida": {"type": "conversation"},
            "agradecimiento": {"type": "conversation"},
            "interaccion": {"type": "conversation"},
            "fallback": {"type": "conversation"}
        }
        
        result = intent_map.get(intent_name, {"type": "conversation"})
        params = self.extraer_entidades(text, intent_name)
        
        if intent_name == "buscar_web" and not params.get("consulta"):
            params["consulta"] = text
        
        result["params"] = params
        result["intent_name"] = intent_name
        return result
    
    def get_response(self, intent_name):
        responses = {
            "saludo": "¡Hola! ¿Cómo puedo ayudarte?",
            "despedida": "¡Hasta luego! Que tengas un buen día.",
            "agradecimiento": "¡De nada! Para eso estoy.",
            "interaccion": "Puedo abrir programas, reproducir música, buscar en internet, controlar el volumen y el sistema. ¿Qué necesitas?",
            "fallback": "Lo siento, no entendí eso. Intenta con un comando claro o pregúntame qué puedo hacer."
        }
        return responses.get(intent_name, responses["fallback"])