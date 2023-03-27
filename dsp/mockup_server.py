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
from pydantic import BaseModel
from datetime import datetime
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


from rrc.dsp.mockup_information import MOCK_PARTNUMBER
from rrc.dsp.mockup_information import PART_INFORMATION


@app.get("/")
async def root():
    return {"message": "Hallo Welt!"}


@app.get("/GET_SERIAL_NUMBER_FOR_UDI", status_code=status.HTTP_200_OK)
async def get_serial(test_type, station_id, line_id, test_socket, udi, response: Response):
    global next_serial, lock_next_serial, lock_serial_db

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    #_product_name = "RRC2020B"
    #_mock = MOCK_PARTNUMBER[_product_name]
    if not (("CELL" in udi) or ("PCBA" in udi)):
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return { "error": "UDI is blacklisted", "code": 7, "udi": udi }

    #_serial = random.randint(1, 47236513)
    async with lock_next_serial:
        next_serial += 1
        # some other thread-safe code here
        _locked_serial = str(next_serial)

    async with lock_serial_db:
        serial_db[next_serial] = udi

    return {
        "udi": udi,
        "serial_number": _locked_serial
    }


@app.post("/SEND_UDI", status_code=status.HTTP_202_ACCEPTED)
async def send_udi(item: UdiItem, response: Response):
    getLogger(__name__, 2).debug(f"Accepted UDI: {item}")
    if 0:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return { "error": "UDI blacklisted", "code": 8,
                 "udi": item.udi, "part_number": item.part_number }

@app.get("/GET_PARAMETER_FOR_WELDING", status_code=status.HTTP_200_OK)
async def get_parameter_for_test_run(station_id, line_id):

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    _product_name = "RRC2020B"
    #_product_name = "RRC2040B"
    #_mock = MOCK_PARTNUMBER[_product_name]
    _mock = PART_INFORMATION[_product_name]

    _fhm = _mock["CELL_WELDING"]
    return {
        "station_id": station_id,
        "line_id": line_id,
        "sequence_revision": _fhm["test_program_id"][1],  # str
        "part_number": _fhm["part_number"][1],        # str
    }


@app.get("/GET_PARAMETER_FOR_TEST_RUN", status_code=status.HTTP_200_OK)
async def get_parameter_for_test_run(test_type, station_id, line_id, test_socket):
    global next_serial, lock_next_serial

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    _product_name = "RRC2020B"
    #_product_name = "RRC2040B"
    #_mock = MOCK_PARTNUMBER[_product_name]
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

@app.post("/REPORT_TEST_RESULT", response_model=Item, status_code=status.HTTP_202_ACCEPTED)
async def report_test_result(item: Item):
    getLogger(__name__, 2).debug(f"Accepted item: {item}")
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
