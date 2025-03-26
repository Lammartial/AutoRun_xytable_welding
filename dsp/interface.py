"""
Interface to DSP of MES system.

Implemented as REST API

"""

from typing import Tuple, List
import json
import requests
import ast
from datetime import datetime
from pathlib import Path
from time import sleep
from random import random

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
        self.LOCAL_RESULT_FILE = Path(local_result_file) if (local_result_file and (local_result_file != "")) else None

    def __str__(self) -> str:
        return f"Interface to DSP REST API on {self.API_BASE_URL}"

    def __repr__(self) -> str:
        return f"DspInterface({self.API_BASE_URL},{self.LOCAL_RESULT_FILE})"

    #----------------------------------------------------------------------------------------------

    def set_result(self, result: str):
        self.api["result"] = result[:1].upper()  # only first letter

    def get_parameter_for_testrun_r2(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> Tuple[bool, dict | str]:
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
            return False, response.json()  # -> bool, str
        try:
            runparams = response.json()
        except Exception as ex:
            _log.error(f"Cannot get valid parameters for testrun from DSP server, please check connection. {ex}")
            return False, None
            #raise

        _log.debug(f"/GET_PARAMETER_FOR_TEST_RUN: {runparams}")
        # pre check the JSON (can be optimized for production)
        if not all(k in runparams for k in ("test_type", "station_id", "test_socket", "test_program_id", "part_number")):
            raise DSPInterfaceError(f"DSP controller get run parameters mssing keys: {runparams}")
        self.api = {**self.api, **runparams}
        return True, runparams  # -> bool, dict


    def get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: str, test_socket: str) -> dict:  # old interface
        ok, runparams = self.get_parameter_for_testrun_r2(test_type, station_id, line_id, test_socket)
        return runparams

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
            raise DSPInterfaceError(f"DSP controller error, cannot send UDI {response.status_code}: {response.json()}")
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
                _log.warning(ast.literal_eval(response.content))
                #_log.debug(response.content.encode("latin-1", "backslashreplace").decode("unicode-escape"))
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

    def ts_get_parameter_for_testrun(self, test_type: str, station_id: str, line_id: int, test_socket: int) -> Tuple[str, str]:
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
            tuple: dsp_ok: bool, error_json: str, (test_program_id: str, part_number: str)

        """

        ok, d = self.get_parameter_for_testrun_r2(test_type, station_id, int(line_id), int(test_socket))
        if ok:
            order = ["test_program_id", "part_number"]
            # TS expects test_program_id and part_number being returned as tuples
            return tuple([(d[field] if d[field] is not None else "") for field in order])
        else:
            # return the error details as JSON string in "part_number"
            # while empty test_program_id indicates the error
            return "", str(d)

    #--------------------------------------------------------------------------------------------------

    def ts_get_serial_number_for_udi(self, udi: str) -> Tuple[bool, str]:
        ok, d = self.get_serial_number_for_udi(
                        self.api["test_type"],
                        self.api["station_id"],
                        self.api["line_id"],
                        self.api["test_socket"],
                        udi)
        if not ok:
            #sn = f"Got Error: {str(d)}" # error from DSP as string
            sn = str(d)  # error from DSP as string
        else:
            sn = d["serial_number"]
        return ok, sn

    #--------------------------------------------------------------------------------------------------

    def ts_send_result_for_testrun(self, result: str, start_datetime: str, execution_time: float, udi: str, serial_number: str) -> None:
        self.api["result"] = result[:1].upper()  # only first letter
        self.api["start_datetime"] = start_datetime
        self.api["execution_time"] = float(execution_time)
        self.api["udi"] = udi  # do not translate to None
        self.api["serial_number"] = serial_number if (serial_number != "") else None  # need to translate to None for DSP
        result_list = self.load_result_list_from_json()
        result_list.append(self.api)
        remaining_list = self.send_result_of_testrun(result_list)
        self.save_result_list_to_json(remaining_list)


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
from rrc.dsp.mockup.information import PART_INFORMATION

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


def _old_test_teststand_line_interfaces(dsp: DspInterface, test_type: str, udi: str, line_id: int = 1, station_id: str = "PDPC1302", socket: int = 0):
    ts_test_run = dsp.ts_get_parameter_for_testrun(test_type, station_id, line_id, socket)
    _log.info(f"TESTRUN: {ts_test_run}")
    if test_type == "EOL_TEST":
        # at this test type we have read the serial number
        serial = udi
        udi = None
    else:
        ok, serial = dsp.ts_get_serial_number_for_udi(udi)
        _log.info(f"SERIAL: {serial}")


# Test the sequence of interfaces in a line in order
def test_teststand_line_interfaces(
        _API_URL,
        line_id: int = 1,
        udi_cell: str = "1CELL000000005A2",
        udi_pcba: str = "1PCBA163512635",
        test_result: str = "P"
    ) -> None:

    serial = None
    if (len(_API_URL.split(":")) == 3):
        # use own, single port, e.g. our mockup server
        dsp_cell   = DspInterface(_API_URL, None)      # CELL test socket / ws102
        dsp_pcba   = DspInterface(_API_URL, None)      # PCBA test socket / ws103
        dsp_core   = DspInterface(_API_URL, None)      # Corepack test socket / ws111
        dsp_eol    = DspInterface(_API_URL, None)      # EOL test socket / ws113
        dsp_lean_par = DspInterface(_API_URL, None)    # = Corepack test socket / ws111
        dsp_lean = DspInterface(_API_URL, None)    # EOL test socket / ws113
        dsp_weld = DspInterface(_API_URL, None)        # welding station ws112
    else:
        # use the standard ports from Orbis
        _line_offset = 10 * (line_id - 1)
        dsp_cell   = DspInterface(f"{_API_URL}:{9925 + _line_offset}", None)      # CELL test socket / ws102
        dsp_pcba   = DspInterface(f"{_API_URL}:{9926 + _line_offset}", None)      # PCBA test socket / ws103
        dsp_core   = DspInterface(f"{_API_URL}:{9927 + _line_offset}", None)      # Corepack test socket / ws111
        dsp_eol    = DspInterface(f"{_API_URL}:{9928 + _line_offset}", None)      # EOL test socket / ws113
        dsp_lean_par = DspInterface(f"{_API_URL}:{9927 + _line_offset}", None)    # = Corepack test socket / ws111
        dsp_lean = DspInterface(f"{_API_URL}:{9928 + _line_offset}", None)        # EOL test socket / ws113
        dsp_weld = DspInterface(f"{_API_URL}:{9929 + _line_offset}", None)        # welding station ws112

    #----------------------
    # CELL TEST
    # request parameter
    if 0:
        _test_run_1 = dsp_cell.ts_get_parameter_for_testrun("CELL_TEST", "DUMMY_1", line_id, 0)
        _log.info(f"TESTRUN: {_test_run_1}")
        # simulate test
        sleep(1)
        # send result to DSP
        dsp_cell.ts_send_result_for_testrun(
            test_result,
            datetime.utcnow().isoformat(),
            (2 + random()*3),  # simulate execution time
            udi_cell,
            serial
        )

    #----------------------
    # WELDING
    # request parameter
    if 0:
        _welding_1 = dsp_weld.ts_get_parameter_for_testrun("CELL_WELDING", "DUMMY_2", line_id, 0)
        _log.info(f"WELDING: {_welding_1}")
        ok, response  = dsp_weld.send_udi_upfront(udi_cell)
        _log.info(f"UDI: {ok}/{response}")
        # simulate test
        sleep(1)
        # send result to DSP
        dsp_weld.ts_send_result_for_testrun(
            test_result,
            datetime.utcnow().isoformat(),
            (2 + random()*3),  # simulate execution time
            udi_cell,
            None,
        )

    #----------------------
    # PCBA TEST
    if 0:
        _test_run_2 = dsp_pcba.ts_get_parameter_for_testrun("PCBA_TEST", "DUMMY_3", line_id, 0)
        _log.info(f"TESTRUN: {_test_run_2}")
        # ... more sockets ?
        # simulate test
        sleep(1)
        # send result to DSP
        dsp_pcba.ts_send_result_for_testrun(
            test_result,
            datetime.utcnow().isoformat(),
            (2 + random()*3),  # simulate execution time
            ",".join([udi_cell,udi_pcba]),
            serial
        )

    #----------------------
    # Leanpack TEST
    if 0:
        _test_run_3 = dsp_lean.ts_get_parameter_for_testrun("LEANPACK_TEST", "DUMMY_4", line_id, 0)
        _log.info(f"TESTRUN: {_test_run_3}")

        #dsp_lean.api["part_number"] = "100496-17" # patch
        #dsp_lean.api["test_program_id"] = "100496-17_EOL-Test_A" # patch
        # ... more sockets ?
        if 1:
            _udi_to_send = f"{udi_cell}"
            ok, serial = dsp_lean.ts_get_serial_number_for_udi(_udi_to_send)
            _log.info(f"SERIAL from cell udi: {serial}")
        if 0:
            _udi_to_send = f"{udi_cell},"
            ok, serial = dsp_lean.ts_get_serial_number_for_udi(_udi_to_send)
            _log.info(f"SERIAL from cell udi: {serial}")
        if 0:
            _udi_to_send = f",{udi_pcba}"
            ok, serial = dsp_lean.ts_get_serial_number_for_udi(_udi_to_send)
            _log.info(f"SERIAL from pcba udi: {serial}")
        if 0:
            _udi_to_send = ",".join([udi_cell, udi_pcba])
            ok, serial = dsp_lean.ts_get_serial_number_for_udi(_udi_to_send)
            _log.info(f"SERIAL: {serial}")
        # simulate test
        sleep(1)
         # # send result to DSP (EOL like, so the serial has to be NONE ZERO!)
        # #dsp_lean_res.api = dsp_lean_par.api.copy()
        # dsp_lean.ts_send_result_for_testrun(
        #     test_result,
        #     datetime.utcnow().isoformat(),
        #     (2 + random()*3),  # simulate execution time
        #     _udi_to_send,
        #     serial
        # )

    #----------------------
    # EOL TEST
    if 1:
        _test_run_4 = dsp_eol.ts_get_parameter_for_testrun("EOL_TEST", "DUMMY_5", line_id, 0)
        _log.info(f"TESTRUN: {_test_run_4}")

        # ... more sockets ?
        if 1:
            _udi_to_send = ",".join([udi_cell, udi_pcba])
            ok, serial = dsp_eol.ts_get_serial_number_for_udi(_udi_to_send)
            _log.info(f"SERIAL from cell,pcba udi: {serial}")

        # simulate test
        sleep(1)
        # # send result to DSP (EOL like, so the serial has to be NONE ZERO!)
        if 1:
            # REWORK Test (Label reprint needs date code appended on SN)
            serial = ",".join((serial, datetime.strftime(datetime.now(), "%Y-%m-%d")))
        # #dsp_lean_res.api = dsp_lean_par.api.copy()
        dsp_eol.ts_send_result_for_testrun(
            test_result,
            #datetime.now(UTC).isoformat(),  # only Python 3.11 and newer
            datetime.utcnow().isoformat(),  # for Python 3.10
            (2 + random()*3),  # simulate execution time
            _udi_to_send,
            serial
        )

    # ...


def test_welder_interface(dsp: DspInterface, udi: str ):
    #test_run = dsp.get_parameter_for_welding("PDPC1302", 1)
    test_run = dsp.get_parameter_for_testrun("CELL_WELDING", "PDPC1302", 1, 0)
    #ts_test_run = dsp.ts_get_parameter_for_testrun("CELL_WELDING", "PDPC1302", 1, 0)
    _log.info(f"TESTRUN: {test_run}")
    #ok, response  = dsp.send_udi_upfront("CELL_WELDING", "PDPC1302", 1, test_run["part_number"], udi )
    ok, response  = dsp.send_udi_upfront(udi)
    _log.info(f"UDI: {ok}/{response}")

    # dsp.ts_send_result_for_testrun(
    #     "Passed",          # result PASS
    #     datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
    #     3.465,             # execution_time
    #     udi,               # udi, scanned string
    #     ""                 # serial number
    # )
    # dsp.ts_send_result_for_testrun(
    #     "Failed",          # result FAILED
    #     datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
    #     2.465,             # execution_time
    #     udi,               # udi, scanned string
    #     ""                 # serial number
    # )
    # dsp.ts_send_result_for_testrun(
    #     "Aborted",         # result Terminate or Abort
    #     datetime.utcnow().isoformat(),  # start_datetime e.g. 2022-12-24T17:28:23.382748
    #     1.465,             # execution_time
    #     udi,               # udi, scanned string
    #     ""                 # serial number
    # )


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # define the JSON file for storage until data sent to MPI
    LOCAL_RESULT_FILE = Path(".") / ".." / "filestore" / "unsent_results.json"
    print(LOCAL_RESULT_FILE.absolute())

    # define the route
    API_URL = "http://127.0.0.1:8000"  # our mockup-server
    #API_URL = "http://172.22.2.40"     # Orbis DSP REST API @RRC (hostname MES-DSP-DE)
    #API_URL = "http://mes-dsp-de.rrc"  # Orbis DSP REST API @RRC
    #API_URL = "http://172.25.100.9"   # ports 9925..9929 Orbis DSP REST API @RRCVN

    #dsp = DspInterface(API_URL, LOCAL_RESULT_FILE)

    for loops in range(10):

        #test_interface(dsp)
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL000000020E2", udi_pcba="", test_result="P", line_id=2)
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL000000020F0", udi_pcba="", test_result="P", line_id=2)
        test_teststand_line_interfaces(API_URL, udi_cell="0CELL9000001CD67", udi_pcba="0PCBA9000001CD67", test_result="P", line_id=2)
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL00000000254", udi_pcba="1PCBA00000000254")
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL00000000255", udi_pcba="1PCBA00000000255", test_result="P")
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL00000000256", udi_pcba="1PCBA00000000256")
        #test_teststand_line_interfaces(API_URL, udi_cell="1CELL00000000257", udi_pcba="1PCBA00000000257")

        # dsp_ws102 = DspInterface(f"{API_URL}:9925", None)
        # dsp_ws103 = DspInterface(f"{API_URL}:9926", None)
        # dsp_ws111 = DspInterface(f"{API_URL}:9927", None)
        # dsp_ws113 = DspInterface(f"{API_URL}:9928", None)
        # dsp_sps   = DspInterface(f"{API_URL}:9929", None)

        #test_teststand_interface(dsp_ws102, "CELL_TEST", "1CELL000000005A2")

        #test_teststand_interface(dsp_ws102, "CELL_TEST", "1CELL163512635")
        #test_teststand_interface(dsp_ws103, "PCBA_TEST", "1PCBA163512635")
        #test_teststand_interface(dsp_ws111, "COREPACK_TEST", "1CELL163512635,1PCBA163512635")
        # test_teststand_interface(dsp_ws111, "COREPACK_TEST", "1CELL0000000059F,1PCBA0000000058C")
        #test_teststand_interface(dsp_ws113, "EOL_TEST", "7")

        #test_welder_interface(dsp_sps, "1CELL0000000050F")  # blacklist
        #test_welder_interface(dsp_sps, "1CELL000000005A2")  # pass

        #test_welder_interface(dsp_sps, "1CELL163512635")


# END OF FILE