"""

Library for Baumer VeriSens AOI Camera access from Teststand.

"""

import time
import socket
import errno
from rrc.eth2serial import Eth2SerialDevice
from binascii import hexlify, unhexlify
from struct import pack, unpack, unpack_from
from collections import OrderedDict


#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__author__ = "Markus Ruth"
__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #






#--------------------------------------------------------------------------------------------------

class VeriSens_XF100M03(Eth2SerialDevice):
    """VeriSens XF100M3 Camera.


    Auflösung
            752 × 480 px

    Sensortyp
            1/3″ CMOS, Monochrom
    Beleuchtung
            integriert, LED Weiß
    LED Klasse
            Risikogruppe 1 (geringes Risiko, EN 62471:2008)
    High Resolution Mode
            Max. 50 Inspektionen pro Sekunde
    High Speed Mode (Reduzierte Auflösung)
            Max. 100 Inspektionen pro Sekunde
    Objektabstand min.
            50 mm
    Anzahl der Jobs (Produkte)
            ≤ 255
    Merkmale je Job
            32
    Signalverarbeitung
            Baumer FEX® 4.0
    Fehlerbildspeicher
            32
    Objektiv
            10 mm
    """

    def __init__(self, resource_str, termination = "\n", trim_termination = True, open_connection = True, pause_on_retry = 10) -> None:
        super().__init__(resource_str, termination, trim_termination, open_connection, pause_on_retry)

        pass

    def __str__(self) -> str:
        return f"Baumer XF100M03 device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"VeriSens_XF100M03({self.host}, {self.port}, termination={self.termination})"


    #----------------------------------------------------------------------------------------------

    def send(self, msg, timeout = 2.0, pause_after_write = None, encoding = "utf-8", retries = 1) -> None:
        return super().send(msg, timeout, pause_after_write, encoding, retries)

    def request(self, msg, timeout = 3, pause_after_write = None, limit = 0, encoding = "utf-8", retries = 1) -> str:
        return super().request(msg, timeout, pause_after_write, limit, encoding, retries)

    #----------------------------------------------------------------------------------------------

    def _num2hex(self, j: int) -> str:
        return f"{j:04x}".upper()


    def _response_state_to_flagdict(self, response_state: str) -> OrderedDict:
        _TRIPPLE_RESULT_BITS = ("none", "active", "failed", "?", "ok", "?", "?", "?")

        assert ((response_state[:2].upper() == "RS") and (len(response_state) >= 10)), ValueError(f"Return value not correct value format: {response_state}.")
        s = int(response_state[2:6], 16)
        job = int(response_state[6:10], 16)
        # V2 - speaking results
        return OrderedDict({
            "internal_fault": ((s >> 15) & 1),
            "backup": _TRIPPLE_RESULT_BITS[((s >> 12) & 0x07)],
            "trigger_possible": ((s >> 11) & 1),
            "job_update": _TRIPPLE_RESULT_BITS[((s >> 8) & 0x07)],            
            "mode": ("none", "recovery", "setup", "?", "test", "?", "?", "?", "run", *("?" for n in range(8)) )[((s >> 4) & 0xf)],
            "photo_shooting": ("?", "external_trigger", "continuous", "?")[((s >> 2) & 3)],
            "protocol_polling": ("?", "polling", "continuous", "?")[((s >> 0) & 3)],
            "job_no": job,
        })
        # V1 - just bits as they come
        return OrderedDict({
            "internal_fault": ((s >> 15) & 1),
            "backup_ok": ((s >> 14) & 1),
            "backup_failed": ((s >> 13) & 1),
            "backup_active": ((s >> 12) & 1),
            "trigger_possible": ((s >> 11) & 1),
            "job_update_ok": ((s >> 10) & 1),
            "job_update_fail": ((s >> 9) & 1),
            "job_update_active": ((s >> 8) & 1),
            "mode_run": ((s >> 7) & 1),
            "mode_test": ((s >> 6) & 1),
            "mode_setup": ((s >> 5) & 1),
            "mode_recovery": ((s >> 4) & 1),
            "photo_shooting_continuous": ((s >> 3) & 1),
            "photo_shooting_external_trigger": ((s >> 2) & 1),
            "protocol_continuous_mode": ((s >> 1) & 1),
            "protocol_polling_mode": ((s >> 0) & 1),
            "job_no": job,
        })


    def get_status(self) -> OrderedDict:
        """Get status information.

        Response is
        response state, 4 bytes ASCII-Hex Status Value, 4 bytes ASCII-Hex number of current job.
        RS              0085                            001A

        Status value bit map:
        ASCII char 1:
            b3: internal fault
            b2: backup ok
            b1: backup failed
            b0: backup active
        ASCII char 2:
            b3: phote shooting, trigger possible
            b2: job update OK
            b1: job update FAIL
            b0: job update active
        ASCII char 3:
            b3: mode is Run-Mode
            b2: mode is Test-Mode
            b1: mode is Setup
            b0: mode is Recovery
        ASCII char 4:
            b3: photo shooting, continuous
            b2: photo shooting, external trigger
            b1: protocol Continuous Mode
            b0: protocol Polling Mode

        Returns:
            str: see above
        """

        res = self.request("GS")
        return self._response_state_to_flagdict(res)


    def init(self) -> None:
        """Sets the Camera into defined default state.

        Returns:
            bool: True - no errors, otherwise False
        """

        res = self.switch_mode("MS")  # parameter mode (stand by)
        res = self.switch_mode("CL")  # line feed        
        self.device_info = [self.request(f"GM{m}")[10:] for m in [
            "0001",  # Gerätetyp
            "0002",  # MAC-address
            "0004",  # Seriennummer
            "0008",  # Firmware-Version
            "0010",  # Hardwarestand
            "0020",  # Gerätename
            "0040",  # Hersteller
            ]]
        #self.device_info = self.request("GM0000")  # this will return all data as string but with spaces delimited which is issue with device name
        res = self.switch_job(1)
        res = self.switch_mode("DP")  # polling mode
        #res = self.switch_mode("DC")  # continuous mode
        res = self.switch_mode("MR")  # mode run
        #time.sleep(0.250)  # first result available after a short pause of 250ms
        #res = self.send("TR")  # trigger first result


    def reboot(self) -> None:
        """Reboot device, a pause of 10s is need before device is up again.
        """
        self.send("VB0000")
        self.close_connection(force=True)


    #----------------------------------------------------------------------------------------------

    def clear_statistics(self, job_no: int = 0) -> bool:
        assert (job_no >= 0), ValueError("Wrong job number, job no need to be >= 0.")
        result = self.request(f"CS{self._num2hex(job_no)}")
        return (result == f"RC{self._num2hex(job_no)}")

    def start_job(self, job_no: int = 0) -> str:
        assert (job_no >= 0), ValueError("Wrong job number, job no need to be >= 0.")
        result = self.request(f"CS{self._num2hex(job_no)}")
        return result

    def get_last_result(self) -> str:
        result = self.request(f"GD")
        assert (result[:2].upper() == "RD"), ValueError(f"Wrong response from device: {result}")        
        data_len = int(result[2:6], 16)
        if data_len > 0:
            pass_fail = result[6]
            alarm = result[7]
            return (result, pass_fail, alarm)
        else:
            return (result,)


    def switch_job(self, job_no: int = 1) -> str:
        assert (job_no > 0), ValueError("Wrong job number, job no need to be > 0.")
        result = self.request(f"SJ{self._num2hex(job_no)}")
        return result


    def switch_mode(self, mode: str = "DC") -> str:
        """
        Mode is one of:
            DC = Data transfer - Continuous Mode
                Die Ergebnisdaten werden autonom nach jeder Auswertung im Modus
                Aktiviert über die Prozessschnittstelle gesendet. Bei Job testen müssen Sie
                dazu den Parameter „Ausgänge aktivieren“ setzen.
            DP = Data transfer - Polling Mode
                Die Ergebnisdaten werden im Modus Aktiviert sowie im Modus
                Parametrieren nur nach Erhalt des GD-Kommandos übertragen.
            MR = Mode switch - Modus Run
                Gerät wird aktiviert
                Daten werden nur autonom gesendet, wenn der Continuous Mode wie
                oben beschrieben aktiviert ist.
            MS = Mode switch - Modus Parametrieren
                Gerät wird in den Modus Parametrieren geschaltet
                keine Übertragung von Ergebnisdaten

        Only valid for Ethernet
            CC = Command delimiter - Carriage return
                 Datenpakete der Prozessschnittstelle werden mit <CR>
                (Hex: 0D, Escape-Sequenz: \r) abgeschlossen
            CL = Command delimiter - Line feed
                Datenpakete der Prozessschnittstelle werden mit <LF>
                (Hex: 0A, Escape-Sequenz: \n) abgeschlossen
            CB = Command delimiter - Both carriage return + line feed
                Datenpakete der Prozessschnittstelle werden mit <CR><LF>
                abgeschlossen
            CN = Command delimite - No sequence
                Datenpakete der Prozessschnittstelle werden nicht mit einer Sequenz
                abgeschlossen.

        Args:
            mode (str, optional): see above. Defaults to "DC".

        Returns:
            str: Response State (RS)
        """

        VALID_MODES = ["DC","DP","MR","MS","CC","CL","CB","CN"]
        assert(mode.upper() in VALID_MODES), ValueError(f"Mode need to be in {VALID_MODES}")
        return self.request(f"SM{mode.upper()}")


    def trigger_analysis(self, part_identification_str: str, pause_for_processing=0.150) -> str:
        #return self.request("TR", timeout=3.0, pause_after_write=0.150)
        if part_identification_str is None or part_identification_str == "":
            self.send("TR")
        else: 
            assert(len(part_identification_str) < 256), ValueError(f"Identification String too long (limit 255) but got length={len(part_identification_str)}.")
            self.send(f"TD{self._num2hex(len(part_identification_str))}{part_identification_str}")
        time.sleep(pause_for_processing)
        return self.get_last_result()

#--------------------------------------------------------------------------------------------------

def test_interface(resource_str: str) -> None:
    dev = VeriSens_XF100M03(resource_str)
    #print("Reboot")
    #dev.reboot()
    #time.sleep(10.0)
    print("Test")
    dev.init()
    print(dev.device_info)
    print(dev.get_status())
    print(dev.get_last_result())
    time.sleep(0.250)
    print("LOOP")
    for n in range(10):
        print(dev.trigger_analysis("0007,1CELL00000000,1PCBA00000000"))
        #print(dev.get_status())
        time.sleep(1)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    CAMERA_RESOURCE_STR = "172.25.101.232:5555"  # VN, line 1

    test_interface(CAMERA_RESOURCE_STR)

    toc = perf_counter()
    print(f"DONE in {toc - tic:0.4f} seconds.")


# END OF FILE