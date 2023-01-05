import time
import asyncio
import datetime

def blocking_io():
    print(f"start blocking_io at {time.strftime('%X')}")
    # Note that time.sleep() can be replaced with any blocking
    # IO-bound operation, such as file operations.
    time.sleep(5)
    print(f"blocking_io complete at {time.strftime('%X')}")

async def machwas():
    for i in range(30):
        print(f"{i}:BLA")
        time.sleep(0.2)

async def main():
    print(f"started main at {time.strftime('%X')}")

    await asyncio.gather(
        asyncio.to_thread(blocking_io),
        machwas(),
        asyncio.sleep(1))

    print(f"finished main at {time.strftime('%X')}")


async def factorial(name, number):
    f = 1
    for i in range(1, number + 1):
        print(f"Task {name}: Compute factorial({number}), currently i={i}...")
        await asyncio.sleep(2.5)
        f *= i
    print(f"Task {name}: factorial({number}) = {f}")
    return f

background_tasks = set()
async def some_coro(param=None):
    print(f"Task {param} started")
    await asyncio.sleep((param + 1)*1.5)
    print(f"Task {param} DONE.")

async def display_date():
    loop = asyncio.get_running_loop()
    end_time = loop.time() + 5.0
    while True:
        print(f"Task DATE: {datetime.datetime.now()}")
        if (loop.time() + 1.0) >= end_time:
            break
        await asyncio.sleep(1)

async def main2():
    # Create some "fire and forget" tasks
    for i in range(10):
        task = asyncio.create_task(some_coro(param=i))
        # Add task to the set. This creates a strong reference.
        background_tasks.add(task)
        # To prevent keeping references to finished tasks forever,
        # make each task remove its own reference from the set after
        # completion:
        task.add_done_callback(background_tasks.discard)

    # Schedule calls *concurrently*:
    L = await asyncio.gather(
        display_date(),
        factorial("A", 2),
        factorial("B", 3),
        factorial("C", 4),
    )
    print(L)

#asyncio.run(display_date())

#asyncio.run(main())
asyncio.run(main2())



