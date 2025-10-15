import socket
import os
import zlib
import time
from pathlib import Path
from rrc.eth2serial import Eth2SerialDevice



class AlgocraftProgrammer(Eth2SerialDevice):
    """
    Class to communicate with Algocraft WriteNow! programmer over TCP/IP.

    """

    def __init__(self, resource_string: str, filestore_path: str | Path) -> None:
        """
        Initialize the AlgocraftProgrammer instance.

        Args:
            resource_string (str): Resource connection string in the format "hostname:port", e.g. "

        """

        super().__init__(resource_string, termination="\n")
        self._filestore_path = Path(filestore_path)


    def set_filenames(self, project_file: str | Path, image_file: str | Path) -> None:
        """
        Set the project and image filenames for the programmer.

        Args:
            project_file (str | Path): Path to the project file.
            image_file (str | Path): Path to the image file.

        """

        self.project_file = self._filestore_path / project_file
        self.image_file = self._filestore_path / image_file


    def execute_command(self, command: str) -> str:
        while True:
            answer = self.request(command, timeout=5.0, encoding="utf-8")
            if answer.endswith(('>','!')):
                return answer  # done
            elif answer.endswith('*'):
                print("busy...")


    def send_file(self, file_path, destination_path) -> bool:
        print(f"Send file {file_path} to {destination_path} on programmer...")
        try:
            # Get file name and size
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
            else:
                print("Invalid file path.\n")
                return False

            # Ping the programmer
            command = "#status -o ping"
            answer = self.execute_command(command)
            if answer != "pong>":
                return False

            # Send '#fs -o send' command and check the answer
            command = f"#fs -o send -f {os.path.join(destination_path, file_name)} -p direct01"
            answer = self.execute_command(command)
            if answer != ">":
                return False

            # Send data size and check the answer
            command = f"@h{file_size:x}\0"
            answer = self.execute_command(command)
            if answer != ">":
                return False

            # Check file size
            if file_size == 0:
                return True

            # Initialize CRC
            crc_calc = 0

            # Open the file and send it in chunks
            with open(file_path, 'rb') as file:
                while chunk := file.read(1024):
                    #socket.sendall(chunk)
                    self.send(chunk, encoding=None)
                    crc_calc = zlib.crc32(chunk, crc_calc)  # Update CRC

            # Finsh CRC
            crc_calc & 0xffffffff

            # Read the answer
            answer = self.request(None, timeout=10.0, encoding="utf-8")
            #socket.settimeout(10)
            #answer = socket.recv(1024).decode('utf-8').strip()
            #print(answer)

            # Get CRC and check if answer ends with '>' (OK)
            if not answer.endswith('>'):
                return False
            crc_read = int(answer.rstrip('>')[1:], 16)

            # Check CRC
            if crc_read != crc_calc:
                print(f"CRC error: read = h{crc_read:x}, expected = h{crc_calc:x}.\n")
                return False

            print(f"File \"{file_name}\" sent to WriteNow! programmer.\n")

            # Wait 100 ms and ping the programmer for checking communication
            time.sleep(0.1)
            command = "#status -o ping"
            answer = self.execute_command(command)
            if answer != "pong>":
                return False

            return True
        except Exception as e:
            print(f"send_file error: {e}")
        return False


    def send_all_files(self) -> bool:
        self.send_file(self.project_file, "projects/")
        self.send_file(self.image_file, "images/")


    def verify_all_files_on_programmer(self, project_file_hash: str, image_file_hash: str) -> bool:
        command = f"#fs -o get -f projects/{self.project_file.name} -p info -r MD5"
        answer = self.execute_command(command)
        if not answer.startswith(f"MD5={project_file_hash}>"):
            print(f"Project file hash mismatch: {answer} (expected: MD5={project_file_hash})")
            return False

        command = f"#fs -o get -f images/{self.image_file.name} -p info -r MD5"
        answer = self.execute_command(command)
        if not answer.startswith(f"MD5={image_file_hash}>"):
            print(f"Image file hash mismatch: {answer} (expected: MD5={image_file_hash})")
            return False

        print("All files verified on programmer.")
        return True





def exe_command(socket: socket.socket, command: str) -> str:
    try:
        # Send the command
        socket.sendall(command.encode('utf-8') + b"\n")
        print(command)

        # Read the answer
        answer = ""
        while True:
            socket.settimeout(5)
            answer = f"{answer}{socket.recv(4096).decode('utf-8')}"

            # Print and return the answer if it ends with '>' (OK) or '!' (ERR)
            if answer.rstrip('\n').endswith(('>', '!')):
                print(answer)
                return answer
            # Print and refresh the answer if it ends with '*' (BUSY)
            elif answer.rstrip('\n').endswith('*'):
                print(answer.rstrip('\n'))
                answer = ""

    except Exception as e:
        print(f"exec_command error: {e}")


def send_file(socket, file_path, destination_path):
    try:
        # Get file name and size
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
        else:
            print("Invalid file path.\n")
            return False

        # Ping the programmer
        command = "#status -o ping"
        answer = exec_command(socket, command).rstrip('\n')
        if answer != "pong>":
            return False

        # Send '#fs -o send' command and check the answer
        command = f"#fs -o send -f {os.path.join(destination_path, file_name)} -p direct01"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != ">":
            return False

        # Send data size and check the answer
        command = f"@h{file_size:x}\0"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != ">":
            return False

        # Check file size
        if file_size == 0:
            return True

        # Initialize CRC
        crc_calc = 0

        # Open the file and send it in chunks
        with open(file_path, 'rb') as file:
            while chunk := file.read(1024):
                socket.sendall(chunk)
                crc_calc = zlib.crc32(chunk, crc_calc)  # Update CRC

        # Finsh CRC
        crc_calc & 0xffffffff

        # Read the answer
        socket.settimeout(10)
        answer = socket.recv(1024).decode('utf-8').strip()
        print(answer)

        # Get CRC and check if answer ends with '>' (OK)
        if not answer.endswith('>'):
            return False
        crc_read = int(answer.rstrip('>')[1:], 16)

        # Check CRC
        if crc_read != crc_calc:
            print(f"CRC error: read = h{crc_read:x}, expected = h{crc_calc:x}.\n")
            return False

        print(f"File \"{file_name}\" sent to WriteNow! programmer.\n")

        # Wait 100 ms and ping the programmer for checking communication
        time.sleep(0.1)
        command = "#status -o ping"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != "pong>":
            return False

        return True
    except Exception as e:
        print(f"send_file error: {e}")


def receive_file(socket, file_path, destination_path):
    try:
        # Check destination path
        if not os.path.exists(destination_path):
            print("Invalid destination path.\n")
            return False

        # Get file name
        file_name = os.path.basename(file_path)

        # Ping the programmer
        command = "#status -o ping"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != "pong>":
            return False

        # Send '#fs -o receive' command and check the answer
        command = f"#fs -o receive -f {file_path} -p direct01"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != ">":
            return False

        # Send "@" and get file size
        command = "@"
        answer = exe_command(socket, command).rstrip('\n')
        if not answer.endswith('>'):
            return False
        file_size = int(answer.rstrip('>')[1:], 16)

        # Check file size
        if file_size == 0:
            return True

        # Send "@"
        command = "@"
        socket.sendall(command.encode('utf-8') + b"\n")
        print(command)

        # Initialize CRC
        crc_calc = 0

        # Open the file and send it in chunks
        with open(f"{os.path.join(destination_path, file_name)}", 'wb') as file:
            byte_to_write = file_size
            while byte_to_write > 0:
                socket.settimeout(10)
                chunk = socket.recv(1024)
                file.write(chunk)
                crc_calc = zlib.crc32(chunk, crc_calc)  # Update CRC
                byte_to_write -= len(chunk)

        # Finsh CRC
        crc_calc & 0xffffffff

        # Send "@" and get the CRC
        command = "@"
        answer = exe_command(socket, command).rstrip('\n')
        if not answer.endswith('>'):
            return False
        crc_read = int(answer.rstrip('>')[1:], 16)

        # Check CRC
        if crc_read != crc_calc:
            print(f"CRC error: read = h{crc_read:x}, expected = h{crc_calc:x}.\n")
            return False

        print(f"File {file_name} received from WriteNow! programmer.\n")

        # Wait 100 ms and ping the programmer
        time.sleep(0.1)
        command = "#status -o ping"
        answer = exe_command(socket, command).rstrip('\n')
        if answer != "pong>":
            return False

        return True
    except Exception as e:
        print(f"receive_file error: {e}")


def main():
    #host = "172.21.5.97"
    host = "172.21.101.38"
    port = 2101
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print(f"\nConnection to {host}:{port}...")
        sock.connect((host, port))
        print("Connected.\n")

        # Transfer the project file to WriteNow! programmer
        _base_path = Path(__file__).parent / "../../Battery-PCBA-Test/filestore/"
        file_path = _base_path / "petalite-test.wnp"           # Path to local project file
        destination_path = "projects/"                         # Destination path for WriteNow! programmer
        if not send_file(sock, str(file_path.absolute()), destination_path):
            print("Error sending project file.\n")

        # # Transfer the image file to WriteNow! programmer
        file_path = _base_path / "petalite-test-image.wni"        # Path to local firmware file
        destination_path = os.path.join("images", "")             # Destination path for WriteNow! programmer
        if not send_file(sock, str(file_path.absolute()), destination_path):
            print("Error sending image file.\n")

        # # Execute the project
        # project_file = os.path.join("projects", "petalite-test.wnp")                   # Project file in programmer "projects" folder
        # sites = "h01"                                                           # Bit mask of the sites to enable
        # command = f"#exec -o prj -f {project_file} -s {sites}"
        # answer = exe_command(sock, command).rstrip('\n')
        # print(f"Command \"{command}\" executed with response: {answer}\n")

def test_crc():
    host = "172.21.101.38"
    port = 2101
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print(f"\nConnection to {host}:{port}...")
        sock.connect((host, port))
        print("Connected.\n")
        command = f"#fs -o get -f images/petalite-test-image.wni -s h01"
        answer = exe_command(sock, command).rstrip('\n')
        print(f"Command \"{command}\" executed with response: {answer}\n")

        command = f"#fs -o get -f images/petalite-test-image.wni -p info -r MD5"
        answer = exe_command(sock, command).rstrip('\n')
        print(f"Command \"{command}\" executed with response: {answer}\n")

if __name__ == "__main__":

    #main()
    test_crc()
    RESOURCE_STR = "172.21.101.38:2101"
    ap = AlgocraftProgrammer(RESOURCE_STR, Path(__file__).parent / "../../Battery-PCBA-Test/filestore/")
    ap.set_filenames("petalite-test.wnp", "petalite-test-image.wni")
    print(ap.execute_command(f"#fs -o get -f images/petalite-test-image.wni -p info -r MD5"))
    #ap.send_all_files()
    ap.verify_all_files_on_programmer("HEINZ", "3AA53EA21D5071EEB02D283137009616")
    #
