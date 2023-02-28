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


#
# Parameters in the form key:value -> key:payload
#  (z.B. “CT-SQ_2020B” mit dann der maximal 40-stelligen Payload in der PRT Description)
#
PART_INFORMATION = {
    #
    # RRC2020B
    #
    "RRC2020B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "sequence_id": ("CT-SQ_2020B", "412031_RRC2020B_Cell-Test_A"),
            "part_number": ("CT-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "sequence_id": ("CW-SQ_2020B", "A"),
            "part_number": ("CW-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "sequence_id": ("PT-SQ_2020B", "411828_RRC2020B_PCBA-Test_A"),
            "part_number": ("PT-PN_2020B", "411828-05"),  # using the pcba part number PN
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "sequence_id": ("CP-SQ_2020B", "412031_RRC2020B_Corepack-Test_A"),
            "part_number": ("CP-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "sequence_id": ("HP-SQ_2020B", "100496_RRC2020B_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "100496-17"),  # using the product number PN
        }
    },
    #
    # RRC2040B
    #
    "RRC2040B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "sequence_id": ("CT-SQ_2040B", "412036_RRC2040B_Cell-Test_A"),
            "part_number": ("CT-PN_2040B", "412036-16"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "sequence_id": ("CW-SQ_2040B", "A"),
            "part_number": ("CW-PN_2040B", "412036-16"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "sequence_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_A"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "sequence_id": ("CP-SQ_2040B", "412036_RRC2040B_Corepack-Test_A"),
            "part_number": ("CP-PN_2040B", "412036-16"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "sequence_id": ("HP-SQ_2040B", "100498_RRC2040B_EOL-Test_A"),
            "part_number": ("HP-PN_2040B", "100498-17"),
        }
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
                "sequence_id": ("FULLY", "UNKNOWN"),
                "part_number": ("REALLY", "UNKNOWN")
            }
    return {
        "test_type": test_type,
        "station_id": station_id,
        "line_id": line_id,
        "test_socket": test_socket,
        "test_program_id": _fhm["sequence_id"][1],  # str
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
