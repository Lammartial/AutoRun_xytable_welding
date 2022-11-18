import logging
import pathlib
import sys

from smartbattery import Battery
from typing import List, Tuple
from time import sleep


class FlashStreamFlasher:
    def __init__(self, battery: Battery):
        self.battery = battery
        self.logger = None
        self.firmware_file = None

    def set_firmware_file(self, firmware_file):
        if isinstance(firmware_file, str):
            firmware_file = (pathlib.Path(firmware_file)).resolve()

        try:
            file = open(firmware_file, "r")
            file.close()
        except (OSError, WindowsError):
            self.logger.error(f"Can't open file: \"{firmware_file}\".")
            raise CantOpenFlashStreamFile()
        except FileNotFoundError:
            self.logger.error(f"File \"{firmware_file}\" does not exist.")
            raise CantOpenFlashStreamFile()

        self.logger.info(f"Using file: \"{firmware_file}\"")
        self.firmware_file = firmware_file

    def setup_logger(self, log_file_path):
        self.logger = logging.getLogger("fs-flasher")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(name)s %(funcName)s %(levelname)-8s %(message)s")
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        if log_file_path is not None and log_file_path != "":
            fh = logging.FileHandler(log_file_path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s %(name)s %(funcName)s %(levelname)-8s %(message)s")
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def prepare_battery(self):
        self.battery.full_access_battery()
        sleep(0.5)
        if not self.battery.is_full_access():
            self.logger.error("Could not set battery to full access mode.")
            raise CantUnsealBatteryError()
        self.logger.info(f"Battery name: {self.battery.device_name()[0]}")

    def process_file(self, is_file_validation: bool):
        validation_result = True
        with open(self.firmware_file, "r") as file:
            line_count = len(file.readlines())  # Get the number of line in the file. Only needed for the progress bar
            file.seek(0)
            line_number = 0
            self.logger.info(f"Line count: {line_count}")
            for current_line in file:
                current_line = current_line.strip()
                line_number += 1
                printProgressBar(line_number, line_count, "Progress")
                if current_line.startswith(";"):
                    # Line is a comment
                    continue

                elif current_line.startswith("X:"):
                    # Wait for x ms
                    current_line_split = current_line.split(" ")
                    if len(current_line_split) != 2:
                        self.logger.error(
                            f"Error in line: {line_number}. Wrong number of arguments. Should be 2 but is {len(current_line_split)}. Line is \"{current_line}\"")
                        validation_result = False
                        continue
                    try:
                        time_ms = int(current_line_split[1])
                    except (ValueError, TypeError):
                        self.logger.error(
                            f"Error in line: {line_number}. Could not parse waiting time. Line is: \"{current_line}\"")
                        validation_result = False
                    if not is_file_validation:
                        sleep(time_ms / 1000.0)
                    continue

                elif current_line.startswith("SWB:"):
                    # Write block
                    result, data = handle_line(current_line[4:], line_number, self.logger)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    self.logger.debug(f"WB: {data}")
                    if not is_file_validation:
                        if self.battery.writeBlock(data[0], bytearray(data[1:])):
                            continue
                        else:
                            self.logger.error(
                                f"Error in SMBus communication during \"write block\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWW:"):
                    # Write word
                    result, data = handle_line(current_line[4:], line_number, self.logger)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    self.logger.debug(f"WW: {data}")
                    word = data[1] | (data[2] << 8)
                    if not is_file_validation:
                        if self.battery.writeWord(data[0], word):
                            continue
                        else:
                            self.logger.error(
                                f"Error in SMBus communication during \"write word\" command in line {line_number}!")
                            break

                elif current_line.startswith("SWC:"):
                    # Write command
                    address, data = handle_line(current_line[4:], line_number, self.logger)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    self.logger.debug(f"WC: {data}")
                    if not is_file_validation:
                        if self.battery.writeBytes(data[0], bytes()):
                            continue
                        else:
                            self.logger.error(
                                f"Error in SMBus communication during \"write command\" command in line {line_number}!")
                            break

                elif current_line.startswith("SCL:"):
                    # Read and compare block
                    address, data = handle_line(current_line[4:], line_number, self.logger)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    register = data[0]
                    length = data[1]
                    expected_data = data[2:]

                    self.logger.debug(f"RB: {register}, {length}")
                    if not is_file_validation:
                        response = self.battery.readBlock(register, 33)
                        if response[1]:
                            received_data = list(response[0])
                        else:
                            self.logger.error(
                                f"Error in SMBus communication during \"compare block\" command in line {line_number}!")
                            break
                        if received_data == expected_data:
                            continue
                        else:
                            self.logger.error(
                                f"Error while comparing data. Expected and received data don't match. (Line: {line_number})")
                            self.logger.error(f"Expected data: {expected_data}")
                            self.logger.error(f"Received data: {received_data}")
                            break

                elif current_line.startswith("SCW:"):
                    # Read and compare word
                    address, data = handle_line(current_line[4:], line_number, self.logger)
                    if not result:
                        if is_file_validation:
                            validation_result = False
                            continue
                        else:
                            break
                    register = data[0]
                    expected_data = int.from_bytes(bytes(data[1:]), "little")
                    self.logger.debug(f"RW: {register}")
                    if not is_file_validation:
                        response = self.battery.readWord(register)
                        if response[1]:
                            received_data = response[0]
                        else:
                            self.logger.error(
                                f"Error in SMBus communication during \"compare word\" command in line {line_number}!")
                            break
                        if received_data == expected_data:
                            continue
                        else:
                            self.logger.error(
                                f"Error while comparing data. Expected and received data don't match. (Line: {line_number})")
                            self.logger.error(f"Line: \"{current_line}\"")
                            self.logger.error(f"Expected data: {expected_data}")
                            self.logger.error(f"Received data: {received_data}")
                            break
                else:
                    self.logger.error(f"Unknown command in line {line_number}: \"{current_line}\"")
                    validation_result = False
                    if not is_file_validation:
                        return 1
        print("")
        return validation_result

    def validate_file(self):
        if self.logger is None:
            self.setup_logger(log_file_path=None)
        elif not self.logger:
            self.logger = logging.getLogger("dummy")

        if self.firmware_file is not None:
            result = self.process_file(is_file_validation=True)
            if result:
                self.logger.info(f"No errors detected in file: \"{self.firmware_file}\".")
            else:
                raise InvalidFlashStreamFile()
            return result
        else:
            self.logger.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

    def program_fw_file(self):
        if self.logger is None:
            self.setup_logger(log_file_path=None)
        elif not self.logger:
            self.logger = logging.getLogger("dummy")
        if self.firmware_file is not None:
            self.prepare_battery()
            result = self.process_file(is_file_validation=False)
            return result
        else:
            self.logger.error("No firmware file specified. Use the set_firmware_file() method to select a firmware file.")
            return False

    def validate_and_program_fw_file(self):
        if self.validate_file():
            self.program_fw_file()


def printProgressBar(value, max_value, label):
    n_bar = 40  # size of progress bar
    j = value / max_value
    sys.stdout.write('\r')
    bar = '█' * int(n_bar * j)
    bar = bar + '-' * int(n_bar * (1 - j))

    sys.stdout.write(f"{label.ljust(10)} | [{bar:{n_bar}s}] {int(100 * j)}% ")
    sys.stdout.flush()


def handle_line(line: str, line_number: int, fs_logger) -> Tuple[bool, List[int]]:
    """Split a line with a list of bytes into a list of integers.

    Args:
        line (str): the line from the flashstream file that should be decoded
        line_number (int): Current line number in the file. Only a reference for error messages
        fs_logger: Logger object for logging error messages

    Returns:
        Tuple: Success as bool and list of integers
    """
    line_split = [i.strip() for i in line.strip().split(" ")]
    if len(line_split) < 2:
        fs_logger.error(f"Error in line: {line_number}: Less than 2 items. (Line: \"{line}\"")
        return False, [0]
    output = []
    for s in line_split:
        try:
            s_int = int(s, 16)
        except ValueError:
            fs_logger.error(f"Error in line: {line_number}: \"{s}\" is not a hexadecimal number")
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


# if __name__ == "__main__":
#     log_file_path = Path("fsf-log-file-{}.log".format(dt.now().strftime("%Y-%m-%dT%H-%M-%S")))
    # fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3412036-02_B_Tansanit_B_RRC2040B.bq.fs")
    # fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3410758-08_bq40z50-R4_A-draft1_Adamite_RRC2140_BMS_Files.bq.fs")
    # flasher = FlashStreamFlasher()
    # if validate_file(fs_file, fs_logger):
    #     pass
    #     program_fw_file(fs_file, fs_logger)
