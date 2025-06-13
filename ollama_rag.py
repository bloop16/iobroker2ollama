import os
import datetime
import json # For RAG tool request/response logging
import traceback # For detailed error logging
import logging
import sys # For flushing stdout if needed

from flask import Flask, request, jsonify, Response
from flask_cors import CORS # For CORS support for the tool endpoint

import ollama
import chromadb

# Configure logging
# This will send log messages of level ERROR and higher to stderr by default
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Globale Konfigurationsvariablen ---
# ChromaDB Konfiguration
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost") # Services on the same server
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", 8087))
CHROMADB_COLLECTION_NAME = os.getenv("CHROMADB_COLLECTION_NAME", "iobroker_events")

# Ollama Konfiguration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434") # Unified Ollama host
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
TOOL_LLM_MODEL = os.getenv("TOOL_LLM_MODEL", "gemma3:4b") # LLM for the RAG tool

# Flask Server Konfiguration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000)) # Single port for the combined app
FLASK_DEBUG_MODE = os.getenv("FLASK_DEBUG_MODE", "False").lower() in ("true", "1", "t")

# RAG Konfiguration
RAG_N_RESULTS = int(os.getenv("RAG_N_RESULTS", 10))

# --- Flask App Initialisierung ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes, particularly for the tool endpoint

# --- Globale Client-Variablen ---
chroma_collection = None
ollama_client = None
 
# --- Client Initialisierungsfunktion ---
def initialize_global_clients():
    global chroma_collection, ollama_client
    print("Initializing global clients...")

    # ChromaDB Client
    try:
        chroma_db_client_instance = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        chroma_collection = chroma_db_client_instance.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
        print(f"Successfully connected to ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}, collection: {CHROMADB_COLLECTION_NAME}")
    except Exception as e:
        logging.error(f"Failed to initialize clients: {e}")
        # Or, if you want to include the stack trace:
        # logging.exception("Failed to initialize clients:")
        sys.exit(1) # Exit if critical initialization fails

    # Ollama Client
    try:
        ollama_client = ollama.Client(host=OLLAMA_HOST)
        models_info_response = ollama_client.list()
        print(f"Successfully initialized Ollama client at {OLLAMA_HOST}.")

        embedding_model_found = False
        tool_model_found = False
        available_model_names = []

        if models_info_response and 'models' in models_info_response and isinstance(models_info_response['models'], list):
            model_list = models_info_response['models']
            available_model_names = [m.get('model') for m in model_list if m.get('model')]
            
            for model_name_on_server in available_model_names:
                if model_name_on_server.startswith(OLLAMA_EMBEDDING_MODEL):
                    embedding_model_found = True
                if model_name_on_server.startswith(TOOL_LLM_MODEL):
                    tool_model_found = True
        
        if embedding_model_found:
            print(f"Embedding model matching '{OLLAMA_EMBEDDING_MODEL}' is available on Ollama (e.g., {', '.join(sorted(list(set(m for m in available_model_names if m.startswith(OLLAMA_EMBEDDING_MODEL)))))}).")
        else:
            print(f"WARNING: Embedding model '{OLLAMA_EMBEDDING_MODEL}' not found on Ollama server at {OLLAMA_HOST}. Please ensure it is pulled. Available models: {available_model_names}")
            # Consider exiting if this model is critical for all operations: exit(1)

        if tool_model_found:
            print(f"Tool LLM model matching '{TOOL_LLM_MODEL}' is available on Ollama (e.g., {', '.join(sorted(list(set(m for m in available_model_names if m.startswith(TOOL_LLM_MODEL)))))}).")
        else:
            print(f"WARNING: Tool LLM model '{TOOL_LLM_MODEL}' not found on Ollama server at {OLLAMA_HOST}. Please ensure it is pulled. Available models: {available_model_names}")
            # Consider exiting if the tool functionality is critical: exit(1)
            
    except Exception as e:
        print(f"FATAL: Error initializing Ollama client or checking models: {e}")
        traceback.print_exc()
        exit(1)

# --- Funktion zum Generieren von Embeddings (aus iobroker_receiver.py) ---
def get_embedding(text):
    if ollama_client is None:
        print("Error: Ollama client is not initialized for get_embedding.")
        return None
    try:
        response = ollama_client.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=text)
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding with Ollama (model: {OLLAMA_EMBEDDING_MODEL}): {e}")
        return None

# --- RAG-Logik (aus rag_tool_server.py) ---
def get_contextual_answer(user_query: str, llm_model_to_use: str, options=None):
    if not ollama_client or not chroma_collection:
        return {"error": "RAG Error: Ollama client or ChromaDB not initialized."}

    print(f"RAG: Processing query for '{llm_model_to_use}': '{user_query}'")
    try:
        query_embedding_response = ollama_client.embeddings(
            model=OLLAMA_EMBEDDING_MODEL,
            prompt=user_query
        )
        query_embedding = query_embedding_response['embedding']

        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=RAG_N_RESULTS,
            include=['documents'] # Only documents are needed for context string
        )
        context_documents = results.get('documents', [[]])[0]
        
        context_str = "Keine spezifischen Informationen zu dieser Frage in der Datenbank gefunden."
        if context_documents:
            context_str = "Relevante Informationen aus der Datenbank:\n"
            for doc in context_documents:
                context_str += f"- {doc}\n" # doc is already the text_for_embedding
        print(f"RAG: Context created:\n{context_str.strip()}")

        system_prompt_for_rag = """Du bist ein hilfreicher Assistent.
Antworte auf die Frage des Benutzers ausschließlich basierend auf dem folgenden Kontext.
Wenn der Kontext nicht ausreicht, um die Frage zu beantworten, sage das bitte.
Formuliere deine Antworten klar und direkt."""
        
        messages_for_llm = [
            {'role': 'system', 'content': system_prompt_for_rag},
            {'role': 'user', 'content': f"Kontext:\n{context_str}\n\nFrage: {user_query}"}
        ]
        
        print("RAG: Sending request to Ollama...")
        response = ollama_client.chat(
            model=llm_model_to_use, 
            messages=messages_for_llm, 
            stream=False, # Tools typically return a single response
            options=options
        )
        if response and response.get('message') and response['message'].get('content'):
            return {"answer": response['message']['content']}
        else:
            print(f"RAG Error: No valid 'content' in LLM response. Response: {response}")
            return {"error": "Keine gültige Antwort vom LLM erhalten."}

    except Exception as e:
        print(f"RAG Error: {e}")
        traceback.print_exc()
        return {"error": f"Fehler in RAG-Pipeline: {str(e)}"}

# --- Health-Check Endpunkt (aus iobroker_receiver.py) ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Combined Python server is running"}), 200

# --- ioBroker Event Receiver Endpunkt ---
@app.route('/iobroker-event', methods=['POST'])
def iobroker_event():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    device_name = data.get('device_name')
    event_type_from_payload = data.get('event_type')
    value = data.get('value')
    data_type = data.get('data_type')
    human_readable_description = data.get('human_readable_description')
    timestamp = data.get('timestamp') 
    location = data.get('location', 'unknown')

    required_fields = {
        "device_name": device_name,
        "event_type": event_type_from_payload,
        "data_type": data_type,
        "human_readable_description": human_readable_description
    }
    missing = [key for key, val in required_fields.items() if val is None]
    if 'value' not in data:
        missing.append('value')

    if missing:
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    text_for_embedding = f"{human_readable_description}"
    if data_type == "boolean":
        text_for_embedding += f" ist {event_type_from_payload}"
    elif data_type == "number":
        text_for_embedding += f": {event_type_from_payload}"
    else: # string, mixed
        text_for_embedding += f": {event_type_from_payload}"
    
    if location and location.lower() != 'unknown' and location.lower() != 'nicht spezifiziert':
        text_for_embedding += f" am Ort '{location}'"
    
    formatted_timestamp_desc = ""
    current_server_time_local = datetime.datetime.now().astimezone()
    event_timestamp_iso = current_server_time_local.isoformat()

    if timestamp:
        try:
            dt_object_utc = datetime.datetime.fromtimestamp(timestamp / 1000, datetime.timezone.utc)
            dt_object_local = dt_object_utc.astimezone()
            formatted_timestamp_desc = dt_object_local.strftime("%H:%M:%S %d.%m.%Y") # GEÄNDERTES FORMAT
            text_for_embedding += f" um {formatted_timestamp_desc}"
            event_timestamp_iso = dt_object_local.isoformat()
        except (TypeError, ValueError) as e:
            print(f"WARN: Could not process timestamp '{timestamp}': {e}. Text: '{text_for_embedding} (timestamp issue)'")
            text_for_embedding += f" (invalid timestamp: {timestamp})"
    else:
        formatted_timestamp_desc = current_server_time_local.strftime("%H:%M:%S %d.%m.%Y") # GEÄNDERTES FORMAT
        text_for_embedding += f" (erfasst um {formatted_timestamp_desc})"

    print(f"Received event for embedding: {text_for_embedding}")
    embedding = get_embedding(text_for_embedding)

    if embedding:
        try:
            ts_for_id = timestamp if timestamp else int(current_server_time_local.timestamp() * 1000)
            doc_id = f"{device_name.replace('.', '-')}_{data_type}_{ts_for_id}_{os.urandom(3).hex()}"
            
            metadata = {
                "device_name": device_name,
                "event_description_from_payload": event_type_from_payload,
                "actual_value": value,
                "data_type": data_type,
                "human_readable_config_description": human_readable_description,
                "location": location,
                "event_timestamp_iso": event_timestamp_iso,
                "text_used_for_embedding": text_for_embedding
            }
            if timestamp:
                metadata["original_timestamp_ms"] = timestamp 
            if formatted_timestamp_desc: 
                metadata["event_timestamp_formatted_readable"] = formatted_timestamp_desc

            chroma_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text_for_embedding],
                metadatas=[metadata]
            )
            print(f"Event stored in ChromaDB with ID: {doc_id}")
            return jsonify({"status": "success", "message": "Event processed and stored", "doc_id": doc_id}), 200
        except Exception as e:
            print(f"Error storing event in ChromaDB: {e}")
            traceback.print_exc()
            return jsonify({"status": "error", "message": f"Error storing event in ChromaDB: {e}"}), 500
    else:
        return jsonify({"status": "error", "message": "Error generating embedding"}), 500

# --- RAG Tool Endpunkt (aus rag_tool_server.py) ---
@app.route('/tools/get_iobroker_data_answer', methods=['POST'])
def iobroker_data_tool_endpoint():
    if not request.is_json:
        print("Tool Endpoint ERROR: Request to /tools/get_iobroker_data_answer was not JSON")
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    request_time_server_local = datetime.datetime.now().astimezone()
    print(f"Tool Endpoint: Incoming request to /tools/get_iobroker_data_answer at {request_time_server_local.isoformat()}:")
    try:
        print(f"  Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except Exception:
        print(f"  Body (raw): {data}")


    user_query = data.get('user_query')
    # Ollama options can be passed through if needed by the tool caller
    ollama_options = data.get('options') 

    if not user_query:
        print("Tool Endpoint ERROR: Parameter 'user_query' is missing.")
        return jsonify({"error": "Parameter 'user_query' is missing"}), 400

    print(f"Tool Endpoint: Calling RAG for query: '{user_query}' with options: {ollama_options}")
    
    result = get_contextual_answer(user_query, TOOL_LLM_MODEL, options=ollama_options) 
    
    response_time_server_local = datetime.datetime.now().astimezone()
    print(f"Tool Endpoint: Sending response from /tools/get_iobroker_data_answer at {response_time_server_local.isoformat()}:")
    status_code = 500 if "error" in result else 200
    print(f"  Status Code: {status_code}")
    try:
        print(f"  Body: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception:
        print(f"  Body (raw): {result}")


    return jsonify(result), status_code

# --- OpenAPI Spezifikation für den Tool Server (aus rag_tool_server.py) ---
@app.route('/openapi.json', methods=['GET'])
def tool_server_openapi_specification():
    print("Serving /openapi.json for tools.")
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "ioBroker Daten-Tool Server",
            "version": "1.0.0",
            "description": "Ein OpenAPI-Server, der ein Tool zur Abfrage von verschiedenen ioBroker-Daten bereitstellt."
        },
        "servers": [
            {
                "url": "/", # Relative URL, as this spec is served by the tool server itself
            }
        ],
        "paths": {
            "/tools/get_iobroker_data_answer": {
                "post": {
                    "summary": "Fragt ioBroker-Daten ab und liefert eine kontextbasierte Antwort.",
                    "operationId": "getIoBrokerDataAnswer",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user_query": {
                                            "type": "string",
                                            "description": "Die Frage des Benutzers zu ioBroker-Daten (z.B. Anwesenheit, Temperatur, Gerätestatus)."
                                        },
                                        "options": {
                                            "type": "object",
                                            "description": "Optionale Ollama-Parameter (z.B. temperature, top_p).",
                                            "additionalProperties": True # Allows any valid Ollama option
                                        }
                                    },
                                    "required": ["user_query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Erfolgreiche Antwort vom Tool",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "answer": {
                                                "type": "string",
                                                "description": "Die vom LLM generierte Antwort basierend auf dem RAG-Kontext."
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "400": {"description": "Ungültige Anfrage", "content": {"application/json": {"schema": {"type": "object", "properties": {"error": {"type": "string"}}}}}},
                        "500": {"description": "Interner Fehler im Tool", "content": {"application/json": {"schema": {"type": "object", "properties": {"error": {"type": "string"}}}}}}
                    }
                }
            }
        }
    }
    return jsonify(openapi_spec)

# --- Hauptausführung ---
if __name__ == '__main__':
    # os.environ["ANONYMIZED_TELEMETRY"] = "False" # Uncomment if needed for chromadb or other libs
    
    initialize_global_clients() # Initialize ChromaDB and Ollama clients
    
    if ollama_client and chroma_collection:
        print(f"Starting Combined Flask Server on {FLASK_HOST}:{FLASK_PORT} (Debug: {FLASK_DEBUG_MODE})")
        print(f"  Serving: ioBroker event receiver, RAG tool, OpenAPI spec, health check.")
        print(f"  ioBroker events endpoint: POST http://{FLASK_HOST}:{FLASK_PORT}/iobroker-event")
        print(f"  RAG tool endpoint: POST http://{FLASK_HOST}:{FLASK_PORT}/tools/get_iobroker_data_answer")
        print(f"  OpenAPI spec: GET http://{FLASK_HOST}:{FLASK_PORT}/openapi.json")
        print(f"  Health check: GET http://{FLASK_HOST}:{FLASK_PORT}/health")
        # For production, consider using a WSGI server like Waitress or Gunicorn
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000) # You can change the host and port
    else:
        print("FATAL: Server could not start due to client initialization errors. Please check logs.")
