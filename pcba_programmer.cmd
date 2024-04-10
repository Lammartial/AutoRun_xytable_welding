@echo OFF
set PYTHONPATH=C:\Production\Python_Libs
rem first parameter is RRC article number of PCBA assembly to program
python.exe pcba_programmer.py %1
rem pause