from typing import Union, Tuple, List
import pathlib
import sys
from time import sleep
from rrc.smartbattery import Battery
from rrc.chipsets import ChipsetTexasInstruments


DEBUG = 1

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

# Initialize the logging
import logging
## init ROOT logger from my_logger.logger_init()
from rrc.logging import logger_init
logger_init() ## init root logger
# get module level logging
_log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #


class FlashStreamFlasher:
    """A class that can update the firmware on a TI BMS with a flash-stream file.
    Flash-stream files can be generated in BQ-Studio from an srec file.
    Flash-stream files contain all the necessary commands to update the firmware:
    X:   Wait for x ms
    SWB: Write a block of data
    SWW: Write a word
    SWC: Write a command (single byte)
    SCL: Read and compare a block
    SCW: Read and compare a word

    This class can parse these files and execute the correct commands.
    In order to update the FW the battery has to be put in full access mode first. This is done automatically in
    prepare_battery().
    MWE:
    flasher = FlashStreamFlasher(battery)
    flasher.set_firmware_file(file_path)
    flasher.validate_and_program_fw_file()
    """
    def __init__(self, battery: ChipsetTexasInstruments):
        """Initialize a class instance."""
        self.battery = battery
        self.firmware_file = None

    def set_firmware_file(self, firmware_file: Union[str, pathlib.Path]):
        """Store the path of the flash-stream file internally if it exists.

        Args:
            firmware_file (str or Path): The firmware file that should be programmed

        Raises:
            CantOpenFlashStreamFile: If the file doesn't exist or cannot be accessed.
        """

        _log = logging.getLogger(__name__)
        if isinstance(firmware_file, str):
            firmware_file = (pathlib.Path(firmware_file)).resolve()

        try:
            file = open(firmware_file, "r")
            file.close()
        except (OSError, WindowsError):
            _log.error(f"Can't open file: \"{firmware_file}\".")
            raise CantOpenFlashStreamFile()
        except FileNotFoundError:
            self._log.error(f"File \"{firmware_file}\" does not exist.")
            raise CantOpenFlashStreamFile()

        _log.info(f"Using file: \"{firmware_file}\"")
        self.firmware_file = firmware_file

    # def setup_logger(self, log_file_path: Union[str, pathlib.Path]):
    #     """Set up a logger that stores a log at log_file_path. If the path is None, the log will be console-only.

    #     Args:
    #         log_file_path (str or Path): path where the log file should be stored. If None, no file will be created.
    #     """
    #     self._log = logging.getLogger("fs-flasher")
    #     self._log.setLevel(logging.DEBUG)
    #     ch = logging.StreamHandler(sys.stdout)
    #     ch.setLevel(logging.INFO)
    #     formatter = logging.Formatter("%(asctime)s %(name)s %(funcName)s %(levelname)-8s %(message)s")
    #     ch.setFormatter(formatter)
    #     self._log.addHandler(ch)

    #     if log_file_path is not None and log_file_path != "":
    #         fh = logging.FileHandler(log_file_path, encoding="utf-8")
    #         fh.setLevel(logging.DEBUG)
    #         formatter = logging.Formatter("%(asctime)s %(name)s %(funcName)s %(levelname)-8s %(message)s")
    #         fh.setFormatter(formatter)
    #         self._log.addHandler(fh)

    def prepare_battery(self):
        """Set the battery to full access mode and log its name.

        Raises:
            CantUnsealBatteryError: If the battery cannot be unsealed.
        """

        _log = logging.getLogger(__name__)
        if not self.battery.enable_full_access():
            self._log.error("Could not set battery to full access mode.")
            raise CantUnsealBatteryError()
        _log.info(f"Battery name: {self.battery.device_name()[0]}")

    #@profile
    def __process_file(self, is_file_validation: bool):
        _log = logging.getLogger(__name__)
        validation_result = True
        with open(self.firmware_file, "r") as file:
            line_count = len(file.readlines())  # Get the number of line in the file. Only needed for the progress bar
            file.seek(0)
            line_number = 0
            _log.info(f"Line count: {line_count}")
            for current_line in file:
                current_line = current_line.strip()
                line_number += 1
                _printProgressBar(line_number, line_count, "Progress")
                if current_line.startswith(";"):
                    # Line is a comment
                    continue

                elif current_line.startswith("X:"):
                    # Wait for x ms
                    current_line_split = current_line.split(" ")
                    if len(current_line_split) != 2:
                        _log.error(
                            f"Error in line: {line_number}. Wrong number of arguments. Should be 2 but is {len(current_line_split)}. Line is \"{current_line}\"")
                        validation_result = False
                        continue
                    try:
                        time_ms = int(current_line_split[1])
                    except (ValueError, TypeError):
                        _log.error(
                            f"Error in line: {line_number}. Could not parse waiting time. Line is: \"{current_line}\"")
                        validation_result = False
                    if not is_file_validation:
                        if time_ms < 25:
                            continue
                        sleep(time_ms / 1000.0)
                    continue

                elif current_line.startswith("SWB:"):
                    # Write block
                    result, data = handle_line(current_line[4:], line_number)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    _log.debug(f"WB: {data}")
                    if not is_file_validation:
                        if self.battery.writeBlock(data[0], bytearray(data[1:])):
                            continue
                        else:
                            _log.error(
                                f"Error in SMBus communication during \"write block\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWW:"):
                    # Write word
                    result, data = handle_line(current_line[4:], line_number)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    _log.debug(f"WW: {data}")
                    word = data[1] | (data[2] << 8)
                    if not is_file_validation:
                        if self.battery.writeWord(data[0], word):
                            continue
                        else:
                            _log.error(
                                f"Error in SMBus communication during \"write word\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWC:"):
                    # Write command
                    address, data = handle_line(current_line[4:], line_number)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    _log.debug(f"WC: {data}")
                    if not is_file_validation:
                        if self.battery.writeBytes(data[0], bytes()):
                            continue
                        else:
                            _log.error(
                                f"Error in SMBus communication during \"write command\" command in line {line_number}!")
                            break

                elif current_line.startswith("SCL:"):
                    # Read and compare block
                    address, data = handle_line(current_line[4:], line_number)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    register = data[0]
                    length = data[1]
                    expected_data = data[2:]

                    _log.debug(f"RB: {register}, {length}")
                    if not is_file_validation:
                        response = self.battery.readBlock(register, 33)
                        if response[1]:
                            received_data = list(response[0])
                        else:
                            _log.error(
                                f"Error in SMBus communication during \"compare block\" command in line {line_number}!")
                            break
                        if received_data == expected_data:
                            continue
                        else:
                            _log.error(
                                f"Error while comparing data. Expected and received data don't match. (Line: {line_number})")
                            _log.error(f"Expected data: {expected_data}")
                            _log.error(f"Received data: {received_data}")
                            break

                elif current_line.startswith("SCW:"):
                    # Read and compare word
                    address, data = handle_line(current_line[4:], line_number)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    register = data[0]
                    expected_data = int.from_bytes(bytes(data[1:]), "little")
                    _log.debug(f"RW: {register}")
                    if not is_file_validation:
                        response = self.battery.readWord(register)
                        if response[1]:
                            received_data = response[0]
                        else:
                            _log.error(
                                f"Error in SMBus communication during \"compare word\" command in line {line_number}!")
                            break
                        if received_data == expected_data:
                            continue
                        else:
                            _log.error(
                                f"Error while comparing data. Expected and received data don't match. (Line: {line_number})")
                            _log.error(f"Line: \"{current_line}\"")
                            _log.error(f"Expected data: {expected_data}")
                            _log.error(f"Received data: {received_data}")
                            break
                else:
                    _log.error(f"Unknown command in line {line_number}: \"{current_line}\"")
                    validation_result = False
                    if not is_file_validation:
                        return 1
        print("")
        return validation_result

    def validate_file(self):
        """Validate the fw file return if no errors were found.

        This runs the same file parser as the programming function, but it doesn't send any commands to the battery.

        Raises:
            InvalidFlashStreamFile: If an error was found in the fw file.

        Returns:
            bool: Result of the validation.
        """
        _log = logging.getLogger(__name__)
        if self.firmware_file is not None:
            result = self.__process_file(is_file_validation=True)
            if result:
                _log.info(f"No errors detected in file: \"{self.firmware_file}\".")
            else:
                raise InvalidFlashStreamFile()
            return result
        else:
            _log.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

    def program_fw_file(self):
        """Prepare the battery and program it with the given fw file.

        Does NOT perform file validation.

        Returns:
            bool: Result of the fw programming.
        """

        _log = logging.getLogger(__name__)
        if self.firmware_file is not None:
            self.prepare_battery()
            result = self.__process_file(is_file_validation=False)
            return result
        else:
            _log.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

    def validate_and_program_fw_file(self):
        """Validate the fw file and then program the battery if the validation was successful.

        This should be your main programming function. Don't use program_fw_file() just by itself.

        Returns:
            bool: The result of validation and programming.
        """
        if self.validate_file():
            return self.program_fw_file()
        else:
            return False


def _printProgressBar(value, max_value, label):
    n_bar = 40  # size of progress bar
    j = value / max_value
    sys.stdout.write('\r')
    bar = '█' * int(n_bar * j)
    bar = bar + '-' * int(n_bar * (1 - j))

    sys.stdout.write(f"{label.ljust(10)} | [{bar:{n_bar}s}] {int(100 * j)}% ")
    sys.stdout.flush()


def handle_line(line: str, line_number: int) -> Tuple[bool, List[int]]:
    """Split a line that contains a list of bytes into a list of integers.

    Args:
        line (str): the line from the flashstream file that should be decoded
        line_number (int): Current line number in the file. Only a reference for error messages
        fs_logger: Logger object for logging error messages

    Returns:
        Tuple: Success as bool and list of integers
    """

    _log = logging.getLogger(__name__)
    line_split = [i.strip() for i in line.strip().split(" ")]
    if len(line_split) < 2:
        _log.error(f"Error in line: {line_number}: Less than 2 items. (Line: \"{line}\"")
        return False, [0]
    output = []
    for s in line_split:
        try:
            s_int = int(s, 16)
        except ValueError:
            _log.error(f"Error in line: {line_number}: \"{s}\" is not a hexadecimal number")
            return False, [0]
        else:
            output.append(s_int)
    return True, output[1:]  # Leave out the first byte. That is just the battery's I2C address.


class FlashStreamError(Exception):
    pass


class CantUnsealBatteryError(FlashStreamError):
    def __init__(self):
        pass

    def __str__(self):
        return "Battery could not be unsealed/full accessed."


class InvalidFlashStreamFile(FlashStreamError):
    def __init__(self):
        pass

    def __str__(self):
        return "There is an error in the flashstream file. Check the log for more infos."


class CantOpenFlashStreamFile(FlashStreamError):
    def __init__(self):
        pass

    def __str__(self):
        return "The flashtream file could not be found or opened. Check the log for more infos."


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime as dt
    from pathlib import Path
    from rrc.eth2i2c import I2CPort
    from smbus import BusMaster, BusMux_PCA9548A

    i2c_port = I2CPort("192.168.1.83", 2101)
    busmaster = BusMaster(i2c_port)
    busmux = BusMux_PCA9548A(i2c_port, address=0x77)
    busmux.setChannel(1)
    bat = Battery(busmaster)
    #print(i2c_port.i2c_bus_scan())
    busmux.setChannel(2)
    # print(i2c_port.i2c_bus_scan())

    t1 = dt.now()
    flasher = FlashStreamFlasher(bat)
    #log_file_path = Path("fsf-log-file-{}.log".format(dt.now().strftime("%Y-%m-%dT%H-%M-%S")))
    #flasher.setup_logger(log_file_path)
    # fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3412036-02_B_Tansanit_B_RRC2040B.bq.fs")
    fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3410758-08_bq40z50-R4_A-draft1_Adamite_RRC2140_BMS_Files.bq.fs")
    flasher.set_firmware_file(fs_file)
    validation_result = flasher.validate_file()
    print(f"Validation result: {validation_result}")
    if validation_result:
        pass
        programming_result = flasher.program_fw_file()
        print(f"Programming result: {programming_result}")

    t2 = dt.now()
    print(f"Programmierzeit: {(t2-t1).seconds}")


# END OF FILE