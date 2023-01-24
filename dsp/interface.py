import json
import requests
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


class DspInterface:

    # data scheme
    api = {
        "test_type": None,        # str: fixed by PC [CORE_PACK_TEST, ...]
        "station_id": None,       # str: fixed by PC (e.g. PC name)
        "line_id": None,          # str: fixed by PC [1,2,3,...]
        "test_socket": None,      # str: -> from TestStand PC before start of sequence, known by TestStand at that time only
        "test_program_id": None,  # str: <- from MPI Server before start of sequence
        "serial_number": None,    # str: <- from MPI Server before start of sequence
        "udi_pcba": None,         # str: -> from TestStand PC scanned by user to start the sequence
        "udi_stack": None,         # str: -> from TestStand PC scanned by user to start the sequence
        "result": None,           # str: -> from TestStand PC at end of sequence P(ASS)/F(AIL)/A(BORT) as text letter
        "execution_time": None,   # float -> from TestStand PC at end of sequence: sec
        "start_datetime": None,   # str: -> from TestStand PC at end of sequence: ISO
    }

    #--------------------------------------------------------------------------------------------------

    def __init__(self, api_base_url: str, local_result_file: str | Path ) -> None:
        self.API_BASE_URL = api_base_url
        self.LOCAL_RESULT_FILE = Path(local_result_file)
    
    def get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> dict:        
        response = requests.get(f"{self.API_BASE_URL}/parameter/{test_type}/{station_id}/{line_id}/{test_socket}")
        # expects JSON of
        # {
        #    "test_station": test_station,
        #    "line_id": line_id,
        #    "test_socket": test_socket,
        #    "test_program_id": a valid subsequence name which will be called,
        #    "serial_number": serial number to assign on PASS to connect UDI and serial number in TestStand Database
        # }
        if response.status_code != 200:
            raise Exception("Cannot start test!", response.json())
        runparams = response.json()
        print(runparams)
        self.api = {**runparams, **self.api} 
        return runparams


    def ifc_get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> tuple:
        """This will convert the dictionary to tuple always in defined order.

        d = {'x': 1 , 'y':2}
        order = ['y','x']
        tuple([d[field] for field in order])

        Args:
            test_type (str): _description_
            station_id (str): _description_
            line_id (str): _description_
            test_socket (str): _description_

        Returns:
            tuple: (test_program_id: str, serial_number: str, udi: (str, str))

        """

        d = self.get_parameter_for_testrun(test_type, station_id, line_id, test_socket)
        order = ["serial_number", "test_program_id"]
        return tuple([d[field] for field in order])


    #--------------------------------------------------------------------------------------------------

    def send_result_of_testrun(self, result_list: list[dict]) -> list[dict]:
        _remaining_list = []
        for result in result_list:
            response = requests.post(f"{self.API_BASE_URL}/result", json=result)
            if response.status_code != 200:
                # did not work, so keep this record for next round
                _remaining_list.append(result)
        return _remaining_list

    #--------------------------------------------------------------------------------------------------

    def load_result_list_from_json(self) -> list[dict]:
        _local_result_file = self.LOCAL_RESULT_FILE
        if not _local_result_file.exists():
            # write empty JSON list
            with open(_local_result_file, "wt") as out_file:
                empty = []
                json.dump(empty, out_file, indent=4)

        with open(_local_result_file, "rt") as in_file:
            _result_list = json.load(in_file)
        return _result_list

    #--------------------------------------------------------------------------------------------------

    def save_result_list_to_json(self, result_list: list[dict]) -> None:
        _local_result_file = self.LOCAL_RESULT_FILE
        with open(_local_result_file, "wt") as out_file:
            json.dump(result_list, out_file, indent=4)

    #--------------------------------------------------------------------------------------------------

    def ifc_send_result_for_testrun(self, result: str, start_datetime: str, execution_time: float, 
                                    udi_pcba: str, udi_stack: str, serial_number: str) -> None:        
        self.api["result"] = result[:1].upper()  # only first letter
        self.api["start_datetime"] = start_datetime
        self.api["execution_time"] = execution_time
        self.api["udi_pcba"] = udi_pcba
        self.api["udi_stack"] = udi_stack
        self.api["serial_number"] = serial_number               
        result_list = self.load_result_list_from_json()
        result_list.append(self.api)
        remaining_list = self.send_result_of_testrun(result_list)
        self.save_result_list_to_json(remaining_list)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":    
    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # define the JSON file for storage until data sent to MPI
    LOCAL_RESULT_FILE = Path(".") / ".." / "filestore" / "unsent_results.json"

    # define the route
    #api_url = "https://production-network.rrc/testcontrol"
    API_URL = "http://127.0.0.1:8000"
    #API_URL = "http://192.168.1.111:8000"

    dsp = DspInterface(API_URL, LOCAL_RESULT_FILE)

    # 1. request information from MPI to start the correct test & UDI:
    #    create the GET route which contains TestStation, LineID and TestSocket
    test_run = dsp.get_parameter_for_testrun("CORE_PACK_TEST", "PDPC1302", 1, 3)
    #test_run = ifc_get_parameter_for_testrun("CORE_PACK_TEST", "PDPC1302", 1, 3)
    # 2. start the test-run of given sequence with teststand
    print("TESTRUN:", test_run)
    # 2.1 load program_id
    # 2.2 scan UDI
    # 2.3 run program sequence

    # 3. combine the test-run result information from TestStand with the provided test_run data
    #    and save it to a JSON file before sending it
    result_list = dsp.load_result_list_from_json()

    # 4. create the result record and append this information to the list and save it first
    #    comes from TestStand:
    test_result = {
        "udi_pcba": "1234567890",  # scanned string
        "udi_stack": None,
        "result": "A",        # depending on TestStand result P(ASS)/F(AIL)/A(BORT) as text letter;
                            # "Abort" could unlock the serial_number at MPI
        "execution_time": 3.465,
        "start_datetime": datetime.utcnow().isoformat()  # e.g. 2022-12-24T17:28:23.382748
                                                    # or we can use UNIX timestamp instead
    }
    to_mpi = {**test_run, **test_result}  # merges both dicts into one, left goes first!
    result_list.append(to_mpi)

    dsp.save_result_list_to_json(result_list)

    # 5. do ONE try to send all the result records to MPI
    remaining_list = dsp.send_result_of_testrun(result_list)

    # 6. save the remaining list for next round
    dsp.save_result_list_to_json(remaining_list)



# END OF FILE