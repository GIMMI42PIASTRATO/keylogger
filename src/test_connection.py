import requests
import json
import sys

# Definisci l'URL del server da testare
SERVER_URL = "http://192.168.1.8:5000"


def test_server_connection():
    """Testa la connessione al server"""
    try:
        print(f"Tentativo di connessione a {SERVER_URL}...")
        response = requests.get(f"{SERVER_URL}/")

        if response.status_code == 200:
            print(f"✅ Connessione riuscita! Risposta: {response.text}")
            return True
        else:
            print(
                f"⚠️ Il server è raggiungibile ma ha restituito un codice di errore: {response.status_code}"
            )
            print(f"Risposta: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Impossibile connettersi al server: {SERVER_URL}")
        print(
            "Verifica che il server sia in esecuzione e che l'indirizzo IP sia corretto."
        )
        return False
    except Exception as e:
        print(f"❌ Errore durante il test di connessione: {str(e)}")
        return False


def test_post_data():
    """Testa l'invio di dati al server"""
    try:
        print(f"\nTentativo di invio dati a {SERVER_URL}/log...")

        # Dati di test da inviare
        test_data = {
            "log": "Questo è un test dal programma di diagnostica",
            "pc_name": "PC_TEST",
            "timestamp": "TEST_TIME",
        }

        # Invia i dati come JSON
        response = requests.post(
            f"{SERVER_URL}/log",
            json=test_data,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            print(f"✅ Dati inviati con successo! Risposta:")
            print(f"Status code: {response.status_code}")
            print(f"Contenuto: {response.text}")
            return True
        else:
            print(f"⚠️ Il server ha restituito un errore: {response.status_code}")
            print(f"Risposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Errore durante l'invio dei dati: {str(e)}")
        return False


def check_server_status():
    """Ottiene informazioni sullo stato del server"""
    try:
        print(f"\nOttenimento stato del server da {SERVER_URL}/status...")
        response = requests.get(f"{SERVER_URL}/status")

        if response.status_code == 200:
            print("✅ Stato del server:")
            data = response.json()
            for key, value in data.items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"⚠️ Errore nell'ottenimento dello stato: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Errore durante il controllo dello stato: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== TEST DI CONNESSIONE AL SERVER KEYLOGGER ===")

    # Test connessione base
    connected = test_server_connection()

    if connected:
        # Test invio dati
        test_post_data()

        # Test stato server
        check_server_status()

    print("\nPremere INVIO per terminare...")
    input()
