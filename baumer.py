"""

Library for Baumer VeriSens AOI Camera access from Teststand.

"""

from rrc.eth2serial import Eth2SerialDevice

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


    def get_status(self) -> str:
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
        return self.request("GS")


    def init(self) -> bool:
        """Sets the Camera into defined default state.

        Returns:
            bool: True - no errors, otherwise False
        """

        self.device_info = [self.request(f"GM{m}") for m in [
            "0001",  # Gerätetyp
            "0002",  # MAC-address
            "0004",  # Seriennummer
            "0008",  # Firmware-Version
            "0010",  # Hardwarestand
            "0020",  # Gerätename
            "0040",  # Hersteller
            ]]

        self.device_info = self.request("GM0000")
        return True


    #----------------------------------------------------------------------------------------------

    def clear_statistics(self, job_no: int = 0) -> bool:
        assert (job_no >= 0), ValueError("Wrong job number, job no need to be >= 0.")
        result = self.request(f"CS{self._num2hex(job_no)}", encoding="utf-8")
        return (result == f"RC{self._num2hex(job_no)}")

    def start_job(self, job_no: int = 0) -> str:
        assert (job_no >= 0), ValueError("Wrong job number, job no need to be >= 0.")
        result = self.request(f"CS{self._num2hex(job_no)}", encoding="ascii")
        return result

    def get_last_result(self) -> str:
        result = self.request(f"GD", encoding="ascii")
        return result

    def switch_job(self, job_no: int = 1) -> str:
        assert (job_no > 0), ValueError("Wrong job number, job no need to be > 0.")
        result = self.request(f"SJ{self._num2hex(job_no)}", encoding="ascii")
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
            mode (str, optional): _description_. Defaults to "DC".

        Returns:
            str: Response State (RS)
        """

        pass


#--------------------------------------------------------------------------------------------------

def test_interface(resource_str: str) -> None:
    dev = VeriSens_XF100M03(resource_str)
    print(dev.start_job(1))



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    CAMERA_RESOURCE_STR = "172.21.101.232:23"  # VN, line 1

    test_interface(CAMERA_RESOURCE_STR)

    toc = perf_counter()
    print(f"DONE in {toc - tic:0.4f} seconds.")


# END OF FILE