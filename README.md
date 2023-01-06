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
  


