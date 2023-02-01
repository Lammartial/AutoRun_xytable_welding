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
from fastapi import FastAPI, Path, status
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

next_serial = 0  # = random.randint(762343, 47236513)
lock_next_serial = asyncio.Lock()

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
    udi: list[str] | None = None      # str: -> from TestStand PC scanned by user to start the sequence
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

@app.get("/parameter/{test_type}/{station_id}/{line_id}/{test_socket}", status_code=status.HTTP_200_OK)
async def read_item(test_type, station_id, line_id, test_socket):
    global next_serial, lock_next_serial, MOCK_PARTNUMBER

    # set the product to test for mockup: "RRC2040B" or "RRC2020B"
    _product_name = "RRC2020B"
    _mock = MOCK_PARTNUMBER[_product_name]

    #_serial = random.randint(1, 47236513)
    async with lock_next_serial:
        next_serial += 1
        # some other thread-safe code here
        _locked_serial = str(next_serial)

    _serial = None
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
            _serial = _locked_serial
        case "EOL_TEST":
            _testprogram = f"{_mock['product'].split('-')[0]}_{_product_name}_EOL-Test_A"
            _part_number = _mock["product"]
            _serial = _locked_serial
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
        "serial_number": _serial,
    }

@app.post("/result", response_model=Item, status_code=status.HTTP_202_ACCEPTED)
async def create_item(item: Item):
    print(item)
    return item


@app.post("/result_yyy")
async def update_item(
        *,
        serial_number: int = Path(title="The serial number of the test item", ge=0, le=999999999999),
        item: Item | None = None,
        ):
    results = {"serial_number": serial_number}
    if item:
        results.update({"item": item})
    return results

# END OF FILE
