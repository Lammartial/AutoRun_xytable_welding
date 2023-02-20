import pyvisa as visa
from time import sleep

from rrc.custom_logging import getLogger, logger_init
logger_init(filename_base=None)  ## init root logger with different filename
_log = getLogger(__name__, 2)


try:  
  resourceManager = visa.ResourceManager() 
  res = resourceManager.list_resources(query='?*')
  _log.info(res)
  #dev = 'TCPIP0::172.21.101.24::49000::SOCKET'
  #dev = 'TCPIP0::172.21.101.24::2049::SOCKET'
  dev = 'TCPIP0::172.21.101.24::INSTR'
  with resourceManager.open_resource(dev) as session:  
    session.timeout = 6000
    print('\n Open Successful!')
    session.read_termination = '\n'
    session.write_termination = '\n'
    #print('CHAN:' +str(session.write('CHAN 1')))
    #print('CHAN:' +str(session.write('CHAN 2')))
    print('IDN:' +str(session.query('CHAN 1; *IDN?')))
    #print('IDN:' +str(session.write('SYSTEM:REMOTE')))
    
    #print('IDN:' +str(session.query('SYSTem:COMMunicate:LAN:RAWSocketport?')))
    session.close()
except Exception as e:
  print('[!] Exception:' +str(e))
finally:
  resourceManager.close()
