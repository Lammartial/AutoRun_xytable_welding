"""
Q&D Mock up for REST API

Install Python packages fastapi and uvicorn as server:

Install with:

    python -m pip install fastapi[all]
or
    conda install fastapi,uvicorn

Start with:

    uvicorn mockup_server:app --reload

"""
from typing import List, Tuple
import random
import asyncio
from fastapi import FastAPI, Response, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from copy import deepcopy
import uuid
import pandas as pd
from rrc.custom_logging import getLogger

app = FastAPI()

next_serial = 0  # = random.randint(762343, 47236513)
lock_next_serial = asyncio.Lock()
serial_db = {}
lock_serial_db = asyncio.Lock()

class Item(BaseModel):
    test_type: str                    # str: fixed by PC [CELL_TEST, PCBA_TEST, CORE_PACK_TEST, EOL_TEST]
    station_id: str                   # str: fixed by PC (e.g. PC name)
    line_id: str                      # str: fixed by PC / Network line
    test_socket: str                  # str: -> from TestStand PC before start of sequence, known by TestStand at that time only
    test_program_id: str              # str: <- from MPI Server before start of sequence
    part_number: str | None           # str -> from MPI Server before start of sequence
    serial_number: str | None = None  # str: <- from MPI Server before start of sequence
    udi: str | None = None            # str: -> from TestStand PC scanned by user or read from the battery to start the sequence
                                      #         CELL_TEST & PCBA_TEST have one UDI;
                                      #         CORPACK_TEST sends two UDI split by comma: udi_cell,udi_pcba
                                      #         EOL_TEST sends string with 3 comma-separated components: serial,udi_cell,pcba_cell
    result: str | None = None         # str: -> from TestStand PC at end of sequence P(ASS)/F(AIL)/A(BORT) as text letter
    execution_time: float | None = None  # float: -> from TestStand PC at end of sequence: sec
    start_datetime: str | None = None    # str: -> from TestStand PC at end of sequence: ISO string


class UdiItem(BaseModel):
    test_type: str                    # str:
    station_id: str                   # str: fixed by PC (e.g. PC name)
    line_id: str                      # str: fixed by PC / Network line
    part_number: str | None           # str -> from MPI Server before start of sequence
    udi: str


from rrc.dsp.mockup_information import PART_INFORMATION, LABEL_PRINTING


#--------------------------------------------------------------------------------------------------
#  TEST
#--------------------------------------------------------------------------------------------------


@app.get("/")
async def root():
    return {"message": "Hallo Welt!"}


#--------------------------------------------------------------------------------------------------
#  SERIAL NUMBER FETCHING
#--------------------------------------------------------------------------------------------------


@app.get("/GET_SERIAL_NUMBER_FOR_UDI", status_code=status.HTTP_200_OK)
async def get_serial(test_type, station_id, line_id, test_socket, udi, response: Response):
    global next_serial, lock_next_serial, lock_serial_db

    if not (("CELL" in udi) or ("PCBA" in udi)):
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return { "error": "UDI is blacklisted", "code": 7, "udi": udi }

    #_serial = random.randint(1, 47236513)
    async with lock_next_serial:
        next_serial += 1
        # some other thread-safe code here
        _locked_serial = str(f"{next_serial:04x}")

    async with lock_serial_db:
        serial_db[next_serial] = udi

    return {
        "udi": udi,
        "serial_number": _locked_serial
    }


#--------------------------------------------------------------------------------------------------
#  SEND UDI
#--------------------------------------------------------------------------------------------------


@app.post("/SEND_UDI", status_code=status.HTTP_202_ACCEPTED)
async def send_udi(item: UdiItem, response: Response):
    getLogger(__name__, 2).debug(f"Accepted UDI: {item}")
    if 0:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return { "error": "UDI blacklisted", "code": 8,
                 "udi": item.udi, "part_number": item.part_number }


#--------------------------------------------------------------------------------------------------
#  PARAMETER FETCHING
#--------------------------------------------------------------------------------------------------


# @app.get("/GET_PARAMETER_FOR_WELDING", status_code=status.HTTP_200_OK)
# async def get_parameter_for_test_run(station_id, line_id):

#     # set the product to test for mockup: "RRC2040B" or "RRC2020B"
#     _product_name = "RRC2020B"
#     #_product_name = "RRC2040B"
#     _mock = PART_INFORMATION[_product_name]

#     _fhm = _mock["CELL_WELDING"]
#     return {
#         "station_id": station_id,
#         "line_id": line_id,
#         "sequence_revision": _fhm["test_program_id"][1],  # str
#         "part_number": _fhm["part_number"][1],        # str
#     }


@app.get("/GET_PARAMETER_FOR_TEST_RUN", status_code=status.HTTP_200_OK)
async def get_parameter_for_test_run(test_type, station_id, line_id, test_socket):
    global next_serial, lock_next_serial

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    #_product_name = "RRC2020B"
    #_product_name = "RRC2020-DR"
    #_product_name = "RRC2040B"
    #_product_name = "RRC2054S"
    #_product_name = "RRC2054-SO"
    #_product_name = "SPINEL"
    #_product_name = "RRC2040-2S"
    _product_name = "RRC2054-2S"
    #_product_name = "RRC2054-2-HM"
    #_product_name = "RRC2054-2-LM"
    #_product_name = "QSB2040B"
    #_product_name = "QSB2054B"
    #_product_name = "QSB2040-2B"
    #_product_name = "QSB2054-2B"
   

    _mock = PART_INFORMATION[_product_name]

    # #_serial = random.randint(1, 47236513)
    # async with lock_next_serial:
    #     next_serial += 1
    #     # some other thread-safe code here
    #     _locked_serial = str(next_serial)

    # _serial = None
    match test_type:
        case "CELLSTACK_TEST":
            #_testprogram = f"{_product_name}_Cell-Test_A"
            #_part_number = f"{_product_name}_CELLSTACK"
            _fhm = _mock["CELL_TEST"]
        case "CELL_TEST":
            _fhm = _mock["CELL_TEST"]
        case "PCBA_TEST":
            _fhm = _mock["PCBA_TEST"]
        case "COREPACK_TEST":
            _fhm = _mock["COREPACK_TEST"]
        case "LEANPACK_TEST":
            _fhm = _mock["LEANPACK_TEST"]
        case "EOL_TEST":
            _fhm = _mock["EOL_TEST"]
        case "HARDPACK_TEST":
            _fhm = _mock["EOL_TEST"]
        case "CELL_WELDING":
            _fhm = _mock["CELL_WELDING"]
        case _:
            _fhm = {
                "test_program_id": ("FULLY", "UNKNOWN"),
                "part_number": ("REALLY", "UNKNOWN")
            }
    return {
        "test_type": test_type,
        "station_id": station_id,
        "line_id": line_id,
        "test_socket": test_socket,
        "test_program_id": _fhm["test_program_id"][1],  # str
        "part_number": _fhm["part_number"][1],      # str
        #"serial_number": _serial,
        #"serial_number": "",
    }


#--------------------------------------------------------------------------------------------------
#  RESULT REPORTING
#--------------------------------------------------------------------------------------------------


@app.post("/REPORT_TEST_RESULT", response_model=Item, status_code=status.HTTP_202_ACCEPTED)
async def report_test_result(item: Item):
    global LABEL_PRINTING

    _log = getLogger(__name__, 2)
    _log.debug(f"Accepted item: {item}")

    if "EOL_TEST" in item.test_type:
        # check option to trigger print of product labels
        #_pn_no_revision = item.part_number.split("-", maxsplit=1)[0]
        _pn = item.part_number
        if _pn in LABEL_PRINTING:
            try:
                _lblprn = LABEL_PRINTING[_pn]
                if _lblprn["enabled"]:
                    # generally enabled
                    if item.result.upper() == "P":                
                        _log.info(f"Label printing: {_lblprn}")
                        # now create the rows for the trigger .dat file
                        _rows_for_datfile = []
                        _ts = datetime.now()  # local time !
                        _serial = None
                        for _content in _lblprn["file_content"]:
                            _ct = deepcopy(_content)  # this is IMPORTANT! otherwise the webserver uses always old data after first execution
                            if _ct["MATNR"] is None:
                                _ct["MATNR"] = _pn  # update the _pn
                            _sn_parts = str(item.serial_number).split(",")
                            if len(_sn_parts) == 2:
                                # we got a correct rework result to process
                                _prn = str(_ct['PRINTERNAME'])
                                _plant = "2000"
                                #item.line_id = 1  # DEBUG ONLY
                                _ct['PRINTERNAME'] = _prn.replace("{01}", _plant).replace("{02}", str(item.line_id))
                                _manufacture_date = datetime.strptime(_sn_parts[1], "%Y-%m-%d")  # we need to convert into datetime object to get the day of week later on
                                _ct["MANUFACTURE_DATE"] =  _manufacture_date.strftime("%Y%m%d")
                                _ct["WEEKDAY"] = "UMTWRFS"[int(_manufacture_date.strftime("%w"))]  # we use our own definition of weekday letters 0=sunday, ... , 6=saturday
                                #_ct["DATECODE"] = _manufacture_date.strftime("%y%U")  # caldendarweek, first week begins with first sunday
                                _ct["DATECODE"] = _manufacture_date.strftime("%y%W")  # caldendarweek, first week begins with first monday
                                
                                # {01}=MODEL CODE(4) {02}=PREASS-REV(2) {03}=MFC(2) {04}=SN-OVERFLOW(2) {05}=S/N(4)
                                #_serial = f"000000{_sn_parts[0]}"[-6:]  # DEVELOP: expand with 0s and get right 6 chars
                                #_serial = _ct["SERIAL"].replace("{01}", _serial[:2]).replace("{02}", _serial[2:])
                                _serial = _sn_parts[0]
                                _ct["SERIAL"] = f"{_serial[:4]} {_serial[4:6]} {_serial[6:8]} {_serial[8:10]} {_serial[10:14]}" 

                                # now combine the code for the printer
                                _da: str = _ct["CODEDATA"]
                                _da = _da.replace("{01}", _ct["MATNR"])\
                                            .replace("{02}", _ct["MATNAME"])\
                                            .replace("{03}", _ct["DATECODE"])\
                                            .replace("{04}", _ct["SERIAL"].replace(" ",""))
                                _ct["CODEDATA"] = _da
                                _ct["CODEDATABIG"] = None
                                # update back
                                _rows_for_datfile.append(_ct)
                        # create the trigger file
                        df = pd.DataFrame(_rows_for_datfile)  #.drop(columns=["include_this"])
                        if _serial:
                            _fp = Path(_lblprn["unc_path"])
                            if _fp.exists() and _fp.is_dir():
                                _datfilename = _fp / f'{_serial.replace(" ", "_")}_{str(uuid.uuid1()).replace("-","").upper()}_{_ts.strftime("%Y%m%d%H%M%S")}.dat'
                                #_datfilename = _fp / "test.csv"  # DEBUG
                                _log.info(f"Created label file: {_datfilename.absolute()}")
                                df.to_csv(_datfilename, index=False, sep="\t")
                    else:
                        # result is not passed -> don't create printfile
                        _log.info(f"Result not pass, cannot print")
            except Exception as ex:
                _log.error(f"Something wrong in label file preparation: {ex}")
                _log.error("EXCEPTION IGNORED.")
        else:
            pass  # printing NOT enabled at all
    return item


# @app.post("/result_yyy")
# async def update_item(
#         *,
#         serial_number: int = Path(title="The serial number of the test item", ge=0, le=999999999999),
#         item: Item | None = None,
#         ):
#     results = {"serial_number": serial_number}
#     if item:
#         results.update({"item": item})
#     return results


# END OF FILE