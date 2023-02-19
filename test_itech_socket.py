import pyvisa as visa
from time import sleep

from rrc.custom_logging import getLogger, logger_init
logger_init(filename_base=None)  ## init root logger with different filename
_log = getLogger(__name__, 2)


try:  
  resourceManager = visa.ResourceManager() 
  dev = 'TCPIP0::172.21.101.24::5025::SOCKET'
  dev = 'TCPIP0::172.21.101.24::inst0::INSTR'
  session = resourceManager.open_resource(dev)
  session.timeout = 5000
  print('\n Open Successful!')
  session.read_termination = '\n'
  session.write_termination = '\r\n'
  print('CHAN:' +str(session.write('CHAN 1')))
  print('CHAN:' +str(session.write('CHAN 2')))
  print('IDN:' +str(session.query('CHAN 2 ; *IDN?')))
  print('IDN:' +str(session.write('SYSTEM:REMOTE')))
  
  #print('IDN:' +str(session.query('SYSTem:COMMunicate:LAN:RAWSocketport?')))
except Exception as e:
  print('[!] Exception:' +str(e))