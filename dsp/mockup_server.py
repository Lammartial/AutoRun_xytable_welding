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
    #name: str
    #description: str | None = None
    #price: float
    #tax: float | None = None
    #tags: list[str] = []
    test_type: str                    # str: fixed by PC [CORE_PACK_TEST, ...]
    station_id: str                   # str: fixed by PC (e.g. PC name)
    line_id: str                      # str: ??? fixed by PC ???
    test_socket: str                  # str:  -> from TestStand PC before start of sequence, known by TestStand at that time only
    test_program_id: str              # str: <- from MPI Server before start of sequence
    part_number: str | None           # str -> from MPI Server before start of sequence
    serial_number: str | None = None  # str: <- from MPI Server before start of sequence
    udi: str | None = None      # str: -> from TestStand PC scanned by user to start the sequence
    #udi_pcba: str | None = None       # str: -> from TestStand PC scanned by user to start the sequence
    #udi_stack: str | None = None      # str: -> from TestStand PC scanned by user to start the sequence
    result: str | None = None         # str: -> from TestStand PC at end of sequence P(ASS)/F(AIL)/A(BORT) as text letter
    execution_time: float | None = None  # float: -> from TestStand PC at end of sequence: sec
    start_datetime: str | None = None    # str: -> from TestStand PC at end of sequence: ISO string

@app.get("/")
async def root():
    return {"message": "Hallo Welt!"}

MOCK_PARTNUMBER = {
    "RRC2020B": {
        "product":        "100496-17",
        "pre_assembly":   "412031-16",
        "pcba":           "411828-05",
    },
    "RRC2040B": {
        "product":        "100498-17",
        "pre_assembly":   "412036-16",
        "pcba":           "411829-05",
    }
}


@app.get("/GET_SERIAL_NUMBER_FOR_UDI", status_code=status.HTTP_200_OK)
async def get_serial(test_type, station_id, line_id, test_socket, udi, response: Response):
    global next_serial, lock_next_serial, lock_serial_db, MOCK_PARTNUMBER

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


@app.get("/VERIFY_SERIAL_NUMBER", status_code=status.HTTP_200_OK)
async def verify_serial(test_type, station_id, line_id, test_socket, part_number, serial_number, response: Response):
    global serial_db, lock_serial_db

    r = None 
    async with lock_serial_db:        
        if serial_number not in serial_db:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            r = { "error": "Serial number not found in db", "code": 8, 
                  "serial_number": serial_number, "part_number": part_number }
        # if serial_number in [1,5,7,11]:
        #     response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        #     r = { "error": "Serial number is blacklisted", "code": 7, 
        #           "serial_number": serial_number, "part_number": part_number }
        else:
            r = {
                "serial_number": serial_number,
                "part_number": part_number, 
                "udi": "76378126378163"
            }
    return r



@app.get("/GET_PARAMETER_FOR_TEST_RUN", status_code=status.HTTP_200_OK)
async def get_parameter_for_test_run(test_type, station_id, line_id, test_socket):
    global next_serial, lock_next_serial, MOCK_PARTNUMBER

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    #_product_name = "RRC2020B"
    _product_name = "RRC2040B"
    _mock = MOCK_PARTNUMBER[_product_name]

    # #_serial = random.randint(1, 47236513)
    # async with lock_next_serial:
    #     next_serial += 1
    #     # some other thread-safe code here
    #     _locked_serial = str(next_serial)

    # _serial = None
    match test_type:
        case "PCBA_TEST":
            _testprogram = f"{_mock['pcba'].split('-')[0]}_{_product_name}_PCBA-Test_A"
            _part_number = _mock["pcba"]
        case "CELLSTACK_TEST":
            _testprogram = f"{_product_name}_Cell-Test_A"
            _part_number = f"{_product_name}_CELLSTACK"
        case "COREPACK_TEST":
            _testprogram = f"{_mock['pre_assembly'].split('-')[0]}_{_product_name}_Corepack-Test_A"
            _part_number = _mock["pre_assembly"]
            #_serial = _locked_serial
        case "EOL_TEST":
            _testprogram = f"{_mock['product'].split('-')[0]}_{_product_name}_EOL-Test_A"
            _part_number = _mock["product"]
            #_serial = _locked_serial
        case _:
            _testprogram = "UNKNOWW"
            _part_number = None
    return {
        "test_type": test_type,
        "station_id": station_id,
        "line_id": line_id,
        "test_socket": test_socket,
        "test_program_id": _testprogram,
        "part_number": _part_number,
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
