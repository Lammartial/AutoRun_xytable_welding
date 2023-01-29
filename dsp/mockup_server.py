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
from fastapi import FastAPI, Path
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
    serial_number: str | None = None  # str: <- from MPI Server before start of sequence
    udi: list[str] | None = None     # str: -> from TestStand PC scanned by user to start the sequence    
    #udi_pcba: str | None = None       # str: -> from TestStand PC scanned by user to start the sequence
    #udi_stack: str | None = None      # str: -> from TestStand PC scanned by user to start the sequence
    result: str | None = None         # str: -> from TestStand PC at end of sequence P(ASS)/F(AIL)/A(BORT) as text letter
    execution_time: float | None = None  # float: -> from TestStand PC at end of sequence: sec
    start_datetime: str | None = None    # str: -> from TestStand PC at end of sequence: ISO string

@app.get("/")
async def root():
    return {"message": "Hallo Welt!"}


@app.get("/parameter/{test_type}/{station_id}/{line_id}/{test_socket}")
async def read_item(test_type, station_id, line_id, test_socket):
    global next_serial, lock_next_serial

    #_serial = random.randint(1, 47236513)
    async with lock_next_serial:
        next_serial += 1
        # some other thread-safe code here
        _serial = str(next_serial)
    match test_type:
        case "PCBA_TEST":
            _testprogram = "411828_A_RRC2020_PCBA-Test"
        case "CELLSTACK_TEST":
            _testprogram = "411828_A_RRC2020_Cell-Test"
        case "COREPACK_TEST":
            _testprogram = "411828_A_RRC2020_Corepack-Test"
        case "EOL_TEST":
            _testprogram = "411828_A_RRC2020_EOL-Test"
        case _:
            _testprogram = "UNKNOWW"
    return {
        "test_type": test_type,
        "station_id": station_id,
        "line_id": line_id,
        "test_socket": test_socket,
        "test_program_id": _testprogram,
        "serial_number": _serial,        
    }

@app.post("/result", response_model=Item)
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
