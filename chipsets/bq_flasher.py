from typing import Union, Tuple, List
import sys
from pathlib import Path
from time import sleep, perf_counter
from rrc.smartbattery import Battery
from rrc.chipsets import ChipsetTexasInstruments
from rrc.ui.progress_bar import ProgressWindow


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


class FlashStreamError(Exception):
    def __init__(self, parent_class):
        self.parent_class = parent_class


class CantUnsealBatteryError(FlashStreamError):

    def __str__(self):
        return f"Battery {self.parent_class.battery} could not be unsealed/full accessed."


class InvalidFlashStreamFileError(FlashStreamError):

    def __str__(self):
        return f"There is an error in the flashstream file {self.parent_class.firmware_file}. Check the log for more infos."


#--------------------------------------------------------------------------------------------------


class BQStudioFileFlasher:
    """
    A class that can update the firmware on a TI BMS with a flash-stream file.
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

    def __init__(self, battery: ChipsetTexasInstruments, firmware_file: Path | str = None,
                 show_progressbar: bool = False, color: str = None, test_socket: int = -1):
        """Initialize a class instance."""
        self.battery = battery
        self._test_socket = int(test_socket)
        self._progress = None
        self._use_threading = False  # this is to enable a short sleep() call after each line to release the GIL lock enabling other threads
        if firmware_file:
            self.set_firmware_file(firmware_file, show_progressbar=show_progressbar, color=color)
        else:
            self.firmware_file = None

    def __str__(self) -> str:
        return f"BQ Studio File flasher {self.battery} using file {self.firmware_file}{', showing progress bar' if self._progress else ''}"

    def __repr__(self) -> str:
        return f"BQStudioFileFlasher({self.battery}, {self.firmware_file}, {True if self._progress else False})"

    #----------------------------------------------------------------------------------------------

    def _print_progress_bar(self, value, max_value, label: str = "Progress"):
        j = value / max_value

        def console():
            n_bar = 40  # size of progress bar
            j = value / max_value
            sys.stdout.write('\r')
            bar = '█' * int(n_bar * j)
            bar = bar + '-' * int(n_bar * (1 - j))
            sys.stdout.write(f"{label.ljust(10)} | [{bar:{n_bar}s}] {int(100 * j)}% ")
            sys.stdout.flush()

        self._progress.set_value(j*100)
        self._progress.show()


    def _handle_line(self, line: str, line_number: int) -> Tuple[bool, List[int]]:
        """Split a line that contains a list of bytes into a list of integers.

        Args:
            line (str): the line from the flashstream file that should be decoded
            line_number (int): Current line number in the file. Only a reference for error messages
            fs_logger: Logger object for logging error messages

        Returns:
            Tuple: Success as bool and list of integers
        """

        _log = getLogger(__name__, DEBUG)
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

    #----------------------------------------------------------------------------------------------
    def set_firmware_file(self, _firmware_file: str | Path, show_progressbar: bool = False, color: str = None) -> None:
        """Store the path of the flash-stream file internally if it exists.

        Args:
            firmware_file (str or Path): The firmware file that should be programmed

        Raises:
            CantOpenFlashStreamFile: If the file doesn't exist or cannot be accessed.
        """

        _log = getLogger(__name__, DEBUG)
        _firmware_file = Path(_firmware_file).resolve()
        try:
            file = open(_firmware_file, "r")
            file.close()
        except (OSError, WindowsError, FileNotFoundError):
            _log.error(f"Can't open file: \"{_firmware_file}\".")
            raise
        _log.info(f"Using file: \"{_firmware_file}\"")
        self.firmware_file = _firmware_file
        if show_progressbar:
            if self._test_socket >= 0:
                self._progress = ProgressWindow(title=f"Program {_firmware_file}", color=color, test_socket=self._test_socket)

    #----------------------------------------------------------------------------------------------
    def __process_file(self, is_file_validation: bool) -> bool:
        _log = getLogger(__name__, DEBUG)
        validation_result: bool = True
        result: bool = True
        prg_result: bool = True
        with open(self.firmware_file, "r") as file:
            line_count = len(file.readlines())  # Get the number of line in the file. Only needed for the progress bar
            file.seek(0)
            line_number = 0
            _log.info(f"Line count: {line_count}")
            if self._progress:
                self._print_progress_bar(line_number, line_count)
            for current_line in file:
                current_line = current_line.strip()
                line_number += 1
                if self._use_threading:
                    sleep(0.00005)

                # we can open the progress bar only here as we need to know the size
                #if self._progress:
                #    self._print_progress_bar(line_number, line_count)

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
                    # hide the progress bar update in the wait times
                    t0 = perf_counter()
                    if not is_file_validation:
                    #if 1: # DEBUG - please remove!
                        while perf_counter() - t0 < (time_ms / 1000):
                            if self._progress:
                                self._print_progress_bar(line_number, line_count)
                            if time_ms < 25:  # cut this wait
                                continue
                    continue

                elif current_line.startswith("SWB:") or current_line.startswith("W:"):
                    # Write block/bytes
                    result, data = self._handle_line(current_line[2:], line_number) if current_line.startswith("W:") else self._handle_line(current_line[4:], line_number)
                    if not result:
                        validation_result = False
                        if is_file_validation:
                            continue
                        else:
                            break
                    _log.debug(f"WB: {data}")
                    if not is_file_validation:
                        if self.battery.writeBlock(data[0], bytearray(data[1:])):
                            continue
                        else:
                            prg_result = False
                            _log.error(
                                f"Error in SMBus communication during \"write block\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWW:"):
                    # Write word
                    result, data = self._handle_line(current_line[4:], line_number)
                    if not result:
                        validation_result = False
                        if is_file_validation:
                            continue
                        else:
                            break
                    _log.debug(f"WW: {data}")
                    word = data[1] | (data[2] << 8)
                    if not is_file_validation:
                        if self.battery.writeWord(data[0], word):
                            continue
                        else:
                            prg_result = False
                            _log.error(
                                f"Error in SMBus communication during \"write word\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWC:"):
                    # Write command
                    address, data = self._handle_line(current_line[4:], line_number)
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
                            prg_result = False
                            _log.error(
                                f"Error in SMBus communication during \"write command\" command in line {line_number}!")
                            break

                elif current_line.startswith("SCL:") or current_line.startswith("C:"):
                    # Read and compare block
                    address, data = self._handle_line(current_line[2:], line_number) if current_line.startswith("C:") else self._handle_line(current_line[4:], line_number)
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
                            prg_result = False
                            _log.error(
                                f"Error in SMBus communication during \"compare block\" command in line {line_number}!")
                            break
                        if received_data == expected_data:
                            continue
                        else:
                            prg_result = False
                            _log.error(
                                f"Error while comparing data. Expected and received data don't match. (Line: {line_number})")
                            _log.error(f"Expected data: {expected_data}")
                            _log.error(f"Received data: {received_data}")
                            break

                elif current_line.startswith("SCW:"):
                    # Read and compare word
                    address, data = self._handle_line(current_line[4:], line_number)
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
                            prg_result = False
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
                        prg_result = False
                        break

        if self._progress:
            self._progress.close()
            self._progress = None

        return validation_result if is_file_validation else prg_result

    #----------------------------------------------------------------------------------------------
    def validate_file(self) -> bool:
        """Validate the fw file return if no errors were found.

        This runs the same file parser as the programming function, but it doesn't send any commands to the battery.

        Raises:
            InvalidFlashStreamFile: If an error was found in the fw file.

        Returns:
            bool: Result of the validation.
        """

        _log = getLogger(__name__, DEBUG)
        if not self.firmware_file:
            _log.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

        result = self.__process_file(is_file_validation=True)
        if result:
            _log.info(f"No errors detected in file: \"{self.firmware_file}\".")
        else:
            raise InvalidFlashStreamFileError(self)
        return result


    #----------------------------------------------------------------------------------------------
    def program_fw_file(self) -> bool:
        """Prepare the battery and program it with the given fw file.

        Does NOT perform file validation.

        Returns:
            bool: Result of the fw programming.
        """

        _log = getLogger(__name__, DEBUG)
        _log.info(f"Flasher: {str(self)}")
        if self.firmware_file is not None:
            if "RECOVERY" not in (self.firmware_file.name.upper()):
                if not self.battery.enable_full_access():
                    _log.error("Could not set battery to full access mode.")
                    raise CantUnsealBatteryError(self)
                _log.info(f"Battery name: {self.battery.device_name()[0]} is unsealed and in full access mode.")
            else:
                _log.info(f"Battery recovery mode, do not check full access mode.")
            result = self.__process_file(is_file_validation=False)
            return result
        else:
            _log.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

    def recover_fw_file(self) -> bool:
        """Prepare the battery and program it with the given fw file.

        Does NOT perform file validation.

        Returns:
            bool: Result of the fw programming.
        """
        result: bool = False
        _log = getLogger(__name__, DEBUG)
        if self.firmware_file is not None:
            return self.__process_file(is_file_validation=False)
        else:
            _log.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False


    def validate_and_program_fw_file(self) -> bool:
        """Validate the fw file and then program the battery if the validation was successful.

        This should be your main programming function. Don't use program_fw_file() just by itself.

        Returns:
            bool: The result of validation and programming.
        """
        if self.validate_file():
            return self.program_fw_file()
        else:
            return False

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from datetime import datetime as dt
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import BusMux, I2CMuxedBus
    from rrc.smbus import BusMaster
    from rrc.chipsets.bq40z50 import BQ40Z50R2

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger
    _log = getLogger(__name__, DEBUG)

    t1 = dt.now()

    bat = None
    fs_file = Path("C:/Production/Battery-PCBA-Test/filestore/SCD_3412031-04_A_Rubin-B_RRC2020B.bq.fs")
    for sock in range(3):
        flasher = BQStudioFileFlasher(bat, firmware_file=fs_file, show_progressbar=True, test_socket=sock)
        #flasher.set_firmware_file(fs_file)

        validation_result = flasher.validate_file()
        _log.info(f"Validation result: {validation_result}")
    #if validation_result:
    #    programming_result = flasher.program_fw_file()
    #    _log.info(f"Programming result: {programming_result}")

    t2 = dt.now()
    _log.info(f"Programmierzeit: {(t2-t1).seconds}")


# END OF FILE