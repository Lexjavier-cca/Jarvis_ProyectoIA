import json
import os
import torch
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class IntentClassifier:
    def __init__(self, model_path="core/bert_intent_model"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encuentra el modelo en {model_path}")
        
        # Cargar tokenizador y modelo
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        # Cargar mapeo de labels
        with open(f"{model_path}/label_mapping.json", "r", encoding="utf-8") as f:
            mapping = json.load(f)
        self.id2label = {int(k): v for k, v in mapping["id2label"].items()}
        self.label2id = mapping["label2id"]
        
        # Configurar dispositivo
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        print(f"✅ Modelo BERT cargado desde {model_path}")
        print(f"📊 Intenciones: {list(self.id2label.values())}")
    
    def classify(self, text):
        """Clasifica la intención y devuelve acción + parámetros"""
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
        
        intent = self.id2label[predicted_class]
        print(f"🎯 Intención: {intent} ({confidence:.2%})")
        
        # Mapeo de intenciones a acciones del sistema
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
        
        result = intent_map.get(intent, {"type": "conversation"})
        params = {}
        
        # Extraer entidades (básico, puedes mejorar)
        if intent == "abrir_programa":
            programas = ['chrome', 'firefox', 'edge', 'vscode', 'spotify', 'word', 'excel', 'notepad', 'calculadora', 'explorador']
            for prog in programas:
                if prog in text.lower():
                    params["app"] = prog
                    break
        elif intent == "reproducir_audio":
            palabras = text.lower().split()
            verbos = ['pon', 'reproduce', 'toca', 'escuchar', 'quiero', 'poner']
            for verbo in verbos:
                if verbo in palabras:
                    idx = palabras.index(verbo)
                    if idx + 1 < len(palabras):
                        resto = palabras[idx+1:]
                        stopwords = ['de', 'la', 'el', 'los', 'las', 'un', 'una']
                        resto = [p for p in resto if p not in stopwords]
                        if resto:
                            params["query"] = ' '.join(resto)
                    break
            if not params.get("query"):
                params["query"] = text
        elif intent == "buscar_web":
            palabras = text.lower().split()
            verbos_busqueda = ['busca', 'googlea', 'investiga', 'encuentra', 'buscar']
            for verbo in verbos_busqueda:
                if verbo in palabras:
                    idx = palabras.index(verbo)
                    if idx + 1 < len(palabras):
                        params["consulta"] = ' '.join(palabras[idx+1:])
                    break
            if not params.get("consulta"):
                params["consulta"] = text
        elif intent == "cambiar_volumen":
            import re
            numeros = re.findall(r'\d+', text)
            if numeros:
                params["level"] = int(numeros[0])
        
        result["params"] = params
        return result
    
    def query_ollama(self, text, model="llama3.2"):
        try:
            response = requests.post(...)
            if response.status_code == 200:
                return response.json().get("response", "No entendí eso.")
            else:
                return "Lo siento, mi cerebro está desconectado."
        except:
            # Respuesta por defecto para saludos
            if "hola" in text.lower() or "saludo" in text.lower():
                return "¡Hola! ¿Cómo puedo ayudarte?"
            elif "gracias" in text.lower():
                return "¡De nada! Para eso estoy."
            elif "adiós" in text.lower() or "chao" in text.lower():
                return "¡Hasta luego! Que tengas un buen día."
            else:
                return "Lo siento, no puedo procesar eso sin Ollama."