"""
Interface to DSP of MES system.

Implemented as REST API

"""

from typing import Tuple
import json
import requests
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 2
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #


getLogger("urllib3.connectionpool", DEBUG)


__version__ = "0.5.0"

class DSPInterfaceError(Exception):
    pass

class DspInterface:

    api = {  # data scheme
        "test_type": None,        # str: fixed by PC [CORE_PACK_TEST, ...]
        "station_id": None,       # str: fixed by PC (e.g. PC name)
        "line_id": None,          # str: fixed by PC [1,2,3,...]
        "test_socket": None,      # str: -> from TestStand PC before start of sequence, known by TestStand at that time only
        "test_program_id": None,  # str: <- from MPI Server before start of sequence
        "part_number": None,      # str: <- from MPI Server before start of sequence
        "serial_number": None,    # str: <- from MPI Server before start of sequence on separate request
        "udi": None,              # str: -> from TestStand PC scanned by user to start the sequence
        "result": None,           # str: -> from TestStand PC at end of sequence P(ASS)/F(AIL)/A(BORT) as text letter
        "execution_time": None,   # float -> from TestStand PC at end of sequence: sec
        "start_datetime": None,   # str: -> from TestStand PC at end of sequence: ISO
    }

    #--------------------------------------------------------------------------------------------------

    def __init__(self, api_base_url: str, local_result_file: str | Path ) -> None:

        self.API_BASE_URL = api_base_url
        self.LOCAL_RESULT_FILE = Path(local_result_file) if local_result_file else None

    def __str__(self) -> str:
        return f"Interface to DSP REST API on {self.API_BASE_URL}"

    def __repr__(self) -> str:
        return f"DspInterface({self.API_BASE_URL},{self.LOCAL_RESULT_FILE})"

    #----------------------------------------------------------------------------------------------

    def set_result(self, result: str):
        self.api["result"] = result[:1].upper()  # only first letter
   
    def get_parameter_for_testrun_r2(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> Tuple[bool, dict]:
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        response = requests.get(f"{self.API_BASE_URL}/GET_PARAMETER_FOR_TEST_RUN",
                                params={"test_type": test_type, "station_id": station_id, "line_id": line_id, "test_socket": test_socket })
        # expects JSON of
        # {
        #    "test_type": test_type,
        #    "station_id": station_id,
        #    "line_id": line_id,
        #    "test_socket": test_socket,
        #    "test_program_id": a valid subsequence name which will be called,
        #    "part_number": a valid part number matching the test_program_id,
        # }
        if response.status_code not in [200, 202, 406]:
            raise DSPInterfaceError(f"DSP controller error, cannot get parameters ({response.status_code}): {response.json()}")
        if response.status_code == 406:  # not acceptable!
            # No production order or such alike
            _log.warning(response.json())
            return False, response.json()
        runparams = response.json()
        _log.debug(f"/GET_PARAMETER_FOR_TEST_RUN: {runparams}")
        # pre check the JSON (can be optimized for production)
        if not all(k in runparams for k in ("test_type", "station_id", "test_socket", "test_program_id", "part_number")):
            raise DSPInterfaceError(f"DSP controller get run parameters mssing keys: {runparams}")
        self.api = {**self.api, **runparams}
        return True, runparams


    def get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> dict:  # old interface
        ok, runparams = self.get_parameter_for_testrun_r2(test_type, station_id, line_id, test_socket)
        return runparams

    #----------------------------------------------------------------------------------------------

    def verify_serial_number(self, test_type: str, station_id: str, line_id: str, test_socket: str, part_number:str, serial_number: str) -> Tuple[bool, dict]:
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        response = requests.get(f"{self.API_BASE_URL}/VERIFY_SERIAL_NUMBER",
                                params={"test_type": test_type, "station_id": station_id, "line_id": line_id, "test_socket": test_socket,
                                        "serial_number": serial_number, "part_number": part_number})
        # expects JSON of
        # {
        #    "serial_number": serial_number,
        #    "part_number": part_number,
        #    "udi": "1CELL1296237,1PCBA2713282"
        # }
        if response.status_code not in [200, 202, 406]:
            pass
        if response.status_code == 406:  # not acceptable!
            # Serial number black listed or any other failer with it
            _log.warning(response.json())
            return False, response.json()
        # valid response
        runparams = response.json()
        _log.debug(f"Verified SN: {runparams}")
        # we got a verified SN
        return True, runparams

    #----------------------------------------------------------------------------------------------

    def get_serial_number_for_udi(self, test_type: str, station_id: str, line_id: str, test_socket: str, udi: str) -> Tuple[bool, dict]:
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        # we send only first part of a combined UDI to get the serial number
        #  "1CELL1296237,1PCBA2713282" -> "1CELL1296237"
        # but we may not store it back into our self.api object
        #_udi_cleaned = udi.split(",")[0]
        _udi_cleaned = udi
        response = requests.get(f"{self.API_BASE_URL}/GET_SERIAL_NUMBER_FOR_UDI",
                                params={"test_type": test_type, "station_id": station_id, "line_id": line_id, "test_socket": test_socket, "udi": _udi_cleaned})
        # expects JSON of
        # {
        #    "udi": _udi_cleaned,
        #    "serial_number": serial_number,
        # }
        if response.status_code not in [200, 202, 406]:
            raise DSPInterfaceError(f"DSP controller error, cannot get serial number {response.status_code}: {response.json()}")
        if response.status_code == 406:  # not acceptable!
            # Serial number black listed
            _log.warning(response.json())
            return False, response.json()
        # valid response
        runparams = response.json()
        _log.debug(f"Request SN: {runparams}")
        if _udi_cleaned != runparams["udi"]:
            raise DSPInterfaceError(f"DSP controller error, got wrong UDI for serial number back: {runparams['udi']}, expected {_udi_cleaned}")
        runparams["udi"] = udi  # replace the potential half UDI by the full one from parameter list
        # we got a valied SN
        self.api = {**self.api, **runparams}
        return True, runparams

    #--------------------------------------------------------------------------------------------------

    # def send_udi_upfront(self, test_type: str, station_id: str, line_id: str, part_number: str, udi: str) -> Tuple[bool, dict]:
    #     _log = getLogger(__name__, DEBUG)
    #     data = {
    #         "test_type": test_type, #self.api["test_type"],
    #         "station_id": station_id, #self.api["station_id"],
    #         "line_id": line_id, #self.api["line_id"],
    #         "part_number": part_number, #self.api["part_number"],
    #         "udi": udi
    #     }
    def send_udi_upfront(self, udi: str) -> Tuple[bool, dict]:
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        data = {
            "test_type": self.api["test_type"],
            "station_id": self.api["station_id"],
            "line_id": self.api["line_id"],
            "part_number": self.api["part_number"],
            "udi": udi
        }
        response = requests.post(f"{self.API_BASE_URL}/SEND_UDI", json=data)
        _log.debug(f"/SEND_UDI: {response}")
        if response.status_code not in [200, 202, 406]:
            raise DSPInterfaceError(f"DSP controller error, cannot update UDI {response.status_code}: {response.json()}")
        if response.status_code == 406:  # not acceptable!
            # Serial number black listed or any other failer with it
            _log.warning(response.json())
            return False, response.json()
        return True, response

    #--------------------------------------------------------------------------------------------------

    def send_result_of_testrun(self, result_list: list[dict]) -> list[dict]:
        _log = getLogger(__name__, DEBUG)
        _remaining_list = []
        for result in result_list:
            _log.debug(f"Result to send: {result}")
            response = requests.post(f"{self.API_BASE_URL}/REPORT_TEST_RESULT", json=result)
            _log.debug(response)
            if response.status_code not in [200, 202]:
                # did not work, so keep this record for next round
                _remaining_list.append(result)
        return _remaining_list

    #--------------------------------------------------------------------------------------------------

    def load_result_list_from_json(self) -> list[dict]:
        if not self.LOCAL_RESULT_FILE:
            return []  # no file set -> always empty list to start with
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
        if not self.LOCAL_RESULT_FILE:
            return
        _local_result_file = self.LOCAL_RESULT_FILE
        with open(_local_result_file, "wt") as out_file:
            json.dump(result_list, out_file, indent=4)

    #----------------------------------------------------------------------------------------------
    # Interfaces to TestStand
    #

    def ts_get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: int, test_socket: int) -> tuple:
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
            tuple: (test_program_id: str, part_number: str)

        """

        d = self.get_parameter_for_testrun(test_type, station_id, int(line_id), int(test_socket))
        order = ["test_program_id", "part_number"]
        #order = ["test_program_id"]
        # expect test_program_id and part_number being tuples
        return tuple([(d[field] if d[field] is not None else "") for field in order])

    #--------------------------------------------------------------------------------------------------

    def ts_get_serial_number_for_udi(self, udi: str) -> str:
        ok, d = self.get_serial_number_for_udi(
                        self.api["test_type"],
                        self.api["station_id"],
                        self.api["line_id"],
                        self.api["test_socket"],
                        udi)
        if not ok:
            sn = f"Got Error: {str(d)}" # error from DSP as string
        else:
            sn = d["serial_number"]
        return ok, sn

    #--------------------------------------------------------------------------------------------------

    def ts_send_result_for_testrun(self, result: str, start_datetime: str, execution_time: float, udi: str, serial_number: str) -> None:
        self.api["result"] = result[:1].upper()  # only first letter
        self.api["start_datetime"] = start_datetime
        self.api["execution_time"] = float(execution_time)
        self.api["udi"] = udi  # do not translate to None
        self.api["serial_number"] = serial_number if (serial_number != "") else None  # meed to translate to None for DSP
        result_list = self.load_result_list_from_json()
        result_list.append(self.api)
        remaining_list = self.send_result_of_testrun(result_list)
        self.save_result_list_to_json(remaining_list)


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
from rrc.dsp.mockup_information import PART_INFORMATION

class DspInterface_SIMULATION(DspInterface):

    def __init__(self, api_base_url: str, local_result_file: str | Path ) -> None:
        # using api_base_url as simulation selector:
        #
        # "RRC2020B" or "RRC2040B"
        #
        self.SIMULATED_PART = api_base_url

    def set_result(self, result: str) -> None:
        pass

    def get_parameter_for_testrun_r2(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> Tuple[bool, dict]:
        d = PART_INFORMATION[self.SIMULATED_PART][test_type]
        for k,v in d.items():
            if isinstance(v, tuple):
                d[k] = v[1]  # we do not need the tuples
        return True, d

    def get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> dict:
        ok, d = self.get_parameter_for_testrun_r2(test_type, station_id, line_id, test_socket)
        return d
    
    def verify_serial_number(self, test_type: str, station_id: str, line_id: str, test_socket: str, part_number:str, serial_number: str) -> Tuple[bool, dict]:
        return True, {}

    def get_serial_number_for_udi(self, test_type: str, station_id: str, line_id: str, test_socket: str, udi: str) -> Tuple[bool, dict]:
        return True, {}

    def send_udi_upfront(self, udi: str) -> Tuple[bool, dict]:
        return True, {}

    def ts_get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: int, test_socket: int) -> tuple:
        d = self.get_parameter_for_testrun(None,None,None,None)
        order = ["test_program_id", "part_number"]
        return tuple([(d[field][1] if d[field][1] is not None else "") for field in order])

    def ts_get_serial_number_for_udi(self, udi: str) -> str:
        return ""

    def ts_send_result_for_testrun(self, result: str, start_datetime: str, execution_time: float, udi: str, serial_number: str) -> None:
        pass

    def send_result_of_testrun(self, result_list: list[dict]) -> list[dict]:
        return [{}]

    def save_result_list_to_json(self, result_list: list[dict]) -> None:
        pass

    def load_result_list_from_json(self) -> list[dict]:
        return [{}]

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

def test_interface(dsp: DspInterface):
    # 1. request information from MPI to start the correct test & UDI:
    #    create the GET route which contains TestStation, LineID and TestSocket
    test_run = dsp.get_parameter_for_testrun("PCBA_TEST", "PDPC1302", 1, 3)

    # 2. start the test-run of given sequence with teststand
    _log.info(f"TESTRUN: {test_run}")
    # 2.1 load program_id
    # 2.2 scan UDI
    # 2.3 run program sequence

    ok, serial = dsp.get_serial_number_for_udi(
                            test_run["test_type"], test_run["station_id"], test_run["line_id"], test_run["test_socket"],
                            "1CLL163512635"
                            )
    _log.info(f"SERIAL: {serial}")

    # 3. combine the test-run result information from TestStand with the provided test_run data
    #    and save it to a JSON file before sending it
    result_list = dsp.load_result_list_from_json()

    # 4. create the result record and append this information to the list and save it first
    #    comes from TestStand:
    test_result = {
        #"udi": "1234567890",  # scanned string
        "result": "A",      # depending on TestStand result P(ASS)/F(AIL)/A(BORT) as text letter;
                            # "Abort" could unlock the serial_number at MPI
        "execution_time": 3.465,
        "start_datetime": datetime.utcnow().isoformat()  # e.g. 2022-12-24T17:28:23.382748
                                                    # or we can use UNIX timestamp instead
    }
    if ok:
        to_mpi = {**test_run, **serial, **test_result}  # merges dicts into one, left goes first!
    else:
        to_mpi = {**test_run, **test_result}
    result_list.append(to_mpi)

    dsp.save_result_list_to_json(result_list)

    # 5. do ONE try to send all the result records to MPI
    remaining_list = dsp.send_result_of_testrun(result_list)

    # 6. save the remaining list for next round
    dsp.save_result_list_to_json(remaining_list)


def test_teststand_interface(dsp: DspInterface, test_type: str, udi: str ):
    ts_test_run = dsp.ts_get_parameter_for_testrun(test_type, "PDPC1302", 1, 3)
    _log.info(f"TESTRUN: {ts_test_run}")
    if test_type == "EOL_TEST":
        # at this test type we have read the serial number
        serial = udi
        udi = None
    else:
        ok, serial = dsp.ts_get_serial_number_for_udi(udi)
        _log.info(f"SERIAL: {serial}")

    dsp.ts_send_result_for_testrun(
        "P",               # result
        datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
        3.465,             # execution_time
        udi,               # udi, scanned string
        serial             # serial number
    )

def test_welder_interface(dsp: DspInterface, udi: str ):
    #test_run = dsp.get_parameter_for_welding("PDPC1302", 1)
    test_run = dsp.get_parameter_for_testrun("CELL_WELDING", "PDPC1302", 1, 0)
    #ts_test_run = dsp.ts_get_parameter_for_testrun("CELL_WELDING", "PDPC1302", 1, 0)
    _log.info(f"TESTRUN: {test_run}")
    #ok, response  = dsp.send_udi_upfront("CELL_WELDING", "PDPC1302", 1, test_run["part_number"], udi )
    ok, response  = dsp.send_udi_upfront(udi)
    _log.info(f"UDI: {ok}/{response}")

    dsp.ts_send_result_for_testrun(
        "Passed",          # result PASS
        datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
        3.465,             # execution_time
        udi,               # udi, scanned string
        ""                 # serial number
    )
    dsp.ts_send_result_for_testrun(
        "Failed",          # result FAILED
        datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
        2.465,             # execution_time
        udi,               # udi, scanned string
        ""                 # serial number
    )
    dsp.ts_send_result_for_testrun(
        "Aborted",         # result Terminate or Abort
        datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
        1.465,             # execution_time
        udi,               # udi, scanned string
        ""                 # serial number
    )


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # define the JSON file for storage until data sent to MPI
    LOCAL_RESULT_FILE = Path(".") / ".." / "filestore" / "unsent_results.json"

    # define the route
    #api_url = "https://production-network.rrc/testcontrol"
    #API_URL = "http://127.0.0.1:8000"
    API_URL = "http://172.22.2.40:9929"  # Orbis DSP REST API @RRC (hostname MES-DSP-DE)
    
    #dsp = DspInterface(API_URL, LOCAL_RESULT_FILE)
    dsp = DspInterface(API_URL, None)

    #test_interface(dsp)
    #test_teststand_interface(dsp, "CELLSTACK_TEST", "1CELL163512635")
    #test_teststand_interface(dsp, "PCBA_TEST", "1PCBA163512635")
    #test_teststand_interface(dsp, "COREPACK_TEST", "1CELL163512635,1PCBA163512635")
    #test_teststand_interface(dsp, "EOL_TEST", "7")

    #test_teststand_interface(dsp, "CELL_WELDING", "1CELL163512635")

    test_welder_interface(dsp, "1CELL163512635")
# END OF FILE