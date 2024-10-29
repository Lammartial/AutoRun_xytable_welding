@echo OFF
if "%PYTHONPATH%" == "" (
    set PYTHONPATH=C:\Production\Python_Libs
)
rem
rem First parameter is RRC article number of PCBA assembly to program.
rem
python.exe pcba_programmer.py %1 --recovery
rem pause