# Python_Libs

Clone this library as "rrc" either into path set at PYTHONPATH environment variable, e.g. C:\Production\Python_Libs\rrc.

Note: using it as a GIT submodule named "rrc" in your project repository is disencouraged as it has too many pitfalls with module imports on same or upper level in the library.

Library:
`git clone http://sv-git.rrc/V-Prod/Python_Libs.git rrc`

Submodule (in a repository base path): (disencouraged!)
`git submodule add http://sv-git.rrc/V-Prod/Python_Libs.git rrc`


## Modules to install for Python

### Installation mit PIP Umgebung

Empfohlen ist die Installation von Python in ein Benutzerdefiniertes Verzeichnis unter C:\Python\... und Verwendung von Paketmanager "PIP".
Um es einfach zu halten, verzichten wir auf virtuelle Umgebungen und installieren bei Bedarf in Zukunft eine neue Python Version (3.11 etc) neben das bereits installierte unter z.B. C:\Python\Python_311 und können dann durch Ändern der Verzeichniseinträge in der Umgebungsvariablen PATH bestimmen, welches Python benutzt werden soll.

### Installation mit Miniconda (conda)

Alternativ zur Installation von Python+PIP mittels download eines Installers von der Website existiert noch die Möglichkeit der Installation von Miniconda3, welche keinerlei Python-Installation auf dem System voraussetzt und beliebige Python Versionen in Umgebungen installieren kann.
Installiert diese für "current user" und dann wählt "Add Miniconda3 to my PATH environment" sowie "Register Miniconda3 as my default Python". Ignoriert die Warnung bei "Add".
Nach der Installation von Miniconda3 existiert eine "base" Umgebung, die sollte man in Ruhe lassen, da sie zur Ausführung der conda tasks benötigt wird. Man sollte stattdessen und eine neue, definierte Umgebung mit prägnantem Namen aufsetzen.

Auch sollte sichergestellt sein, daß das Verzeichnis in dem die Umgebungen installiert werden für alle Benutzer verfügbar ist, denn die Vorgabe ist ein Umgebungsverzeichnis .conda im Benutzerhome.

Zuerst mal conda selbst updaten:
`conda update --name base --channel defaults conda`

- starte Miniconda3 Kommandozeile (am besten gleich in Taskleiste heften)
- "base" Umgebung muß aktiv sein, falls nicht `conda activate base` tippen.
- geeignetes Verzeichnis für die Umgebungen anlegen: `conda config --add envs_dirs C:\Python\conda`
- check `conda config --show envs_dirs` und `conda info`
- neue Umgebung anlegen: `conda create --name prod python=3.10`

zum Ausprobieren lassen sich dann beliebige weitere Umgebungen anlegen und testen:
`conda create --name dev_p311 python=3.11`
(die 3.11 gibts noch nicht (Sep2022))

#### Hinzufügen von conda-forge Kanal für PyVISA

Da PyVISA nicht in den default channels zu finden ist, sondern bei conda-forge, muß man entweder den Kanal explizit angeben:
`conda install --channel conda-forge pyvisa`

Oder man installiert den channel `conda-forge` und hat dann immer Zugriff:
`conda config --add channels conda-forge`

check mit:
`conda config --show channels`

#### Liste der Module

```
# nicht bei Verwendung der CONDA (Miniconda) Umgebung!
pip
wheel

# Alle Umgebungen
typing
pandas
pytz
pyyaml
icmplib

# Debugging (required by TestStand)
debugpy

# Datenübergabe "Context"
pywin32

# MODBUS Geräte via TCP oder RS485/RS232
pymodbus

# SCPI Geräte via VISA
pyvisa

# DATABASE via TCP oder File
SQLAlchemy
pyodbc
pymssql
psycopg2
pymysql
```

### For the lazy guys (copy & paste):

PIP:
`pip wheel typing debugpy numpy==1.23 scipy pandas pytz pymodbus pyvisa SQLAlchemy pyodbc pymssql psycopg2 pymysql pyyaml pywin32 requests fastapi[all] humanfriendly pyelftools pyserial pyserial-asyncio icmplib xlrd`

CONDA:
`typing pyyaml debugpy numpy==1.23 scipy pandas pytz pymodbus pyvisa SQLAlchemy pyodbc pymssql psycopg2 pymysql pywin32 requests fastapi[all] humanfriendly pyelftools pyserial pyserial-asyncio icmplib xlrd`

consider: matplotlib, dash

## Debugging with VSCode

Teststand bietet die Option, die Python-Module zu debuggen.

#### Was NICHT funktioniert:
Generell funktioniert die "Step into" Methode von Teststand nicht. Es gibt ein Connectuon Error seitens VSCode - Ursache unbekannt.

#### Was funktioniert:
Attach to Process ID (PID).
Man muß dazu die Debug-Session in VSCode starten und dann die richtige PID raussuchen: "python" tippen und raten oder man läßt sich die PID beim Test-Start in einer Dialogbox ausgeben (siehe modul `debug_support.py`) und tippt die dann ein. Dann "Connect" drücken und kurz warten bis die Session gestartet ist. Jetzt kann man auf Seiten von Teststand die Dialogbox mit PID schließen und den Testlauf starten.
Es lassen sich Breakpoints auf VSCode Seite nach Belieben setzen oder ändern, solange der von Teststand gestartete Python Prozess am Leben bleibt.

### Umgebungsvariable setzen

PYTHONPATH = C:\Production\Python_Libs

# TestStand Config

- globals nachziehen
- adapter Python 3.10 (version)
    per thread
    reload modified modules before execution
    (enable debug) optional


## Structure

--
  dbcon
    - experimental
  debug
    - debug helper for TestStand as well as test functions for library modules
  eth2serial
    - basic socket handling for ETH to UART
  modbus
    - basic modbus handling using either TCP or RTU
  dsp
    - REST interface to DSP
  ui
    - customized dialogs like scanner dialog

## IVI-VISA / NI-VISA

To uses the VISA drivers with python install VISA shared components from Keysight IO Libraries Suite 2022 Update 2.

Then install pyvisa, modules for use with Python.
As alternative Python-backend you can install pyvisa-py and pygpib modules.
`pyvisa-info` is a command line tool to show the configuration of the backend.

## Network device configuration

  Waveshare Eth2UART (CH9121)
    1. Connect your PC to the adapter using an Ethernet cable.
    2. Use "NetModuleConfig" GUI and file "Conf_CH9121_Barcode_and_LEDanalyzer.cfg" to configure the adapter:
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\Waveshare_Eth2UART_CH9121
    3. Change the IP address if necessary. Port 1 and Port 2 are already preconfigured.

  Eth2I2C (NCD5500)
    1. Connect your PC to the adapter using an Ethernet cable or WiFi network.
    2. Use "NCDConfigToolV2.exe" to configure the adapter:
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\NCD5500_Config_Tool
    3. To find the NCD5500, select the IP address of the PC's Ethernet or WiFi adapter in the combo box.

  Hioki BT3561A
    1. Default IP address of the device is 192.168.1.1
    2. Connect your PC to the device using an Ethernet cable or WiFi network.
    3. You can change the device's LAN interface settings using a web browser and current IP address of the device.
    4. More info:
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\HIOKI BT3561A

  Hioki SW1001
    1. Use Python script hioki-sw1001_set-ip.py.
    2. Connect the LAN cable to the SW1001.
    3. Set communication setting mode switch (DFLT/USER) on the back of the SW1001 to DFLT.
      Default: IP 192.168.0.254, Port 23.
    4. Set the IP of the PC to the same subnetwork. For example 192.168.0.10.
    5. Define the IP address of the SW1001 below.
    6. Run script.
    7. Switch off the SW1001. Set communication setting mode switch (DFLT/USER) to USER. Switch on the device.
    8. New IP has been applied.

  ITECH M3400/M3900
    1. The configuration steps are the same for both devices (MT3400 and MT3900).
    2. See chapter 2.6.3 LAN Interface, page 27 User manual:
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\ITECH IT-M3400

  Keysight DAQ970A
    1. See chapter LAN Settings, page 23 User manual "Benutzerhandbuch_9018-04738":
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\Keysight DAQ





