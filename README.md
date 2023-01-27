# Python_Libs

Clone this library as "rrc" either into path set at PYTHONPATH environment variable, e.g. C:\Production\Python_Libs\rrc.

Note: using it as a GIT submodule named "rrc" in your project repository is disencouraged as it has too many pitfalls with module imports on same or upper level in the library.

Library:
`git clone http://sv-git.rrc/V-Prod/Python_Libs.git rrc`

Submodule (in a repository base path): (disencouraged!)
`git submodule add http://sv-git.rrc/V-Prod/Python_Libs.git rrc`



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


## Network configuration

  Waveshare Eth2UART (CH9121)
    1. Connect your PC to the adapter using an Ethernet cable.
    2. Use "NetModuleConfig" GUI and file "Conf_CH9121_Barcode_and_LEDanalyzer.cfg" to configure the adapter:
      W:\260_Production-Engineering\100_Projekte\Vietnam\060_Testsysteme\Datenblätter_Manuals\Waveshare_Eth2UART_CH9121
    3. Change the IP address if necessary. Port 1 and Port 2 are already preconfigured. 

  Eth2I2C (NCD5500)
    1. Connect your PC to the adapter using an Ethernet cable or WiFi network.
    2. Use "NCDConfigTool.exe" to configure the adapter:
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


  


