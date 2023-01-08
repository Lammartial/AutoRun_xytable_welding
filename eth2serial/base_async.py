
#
# Waveshare by socket connection instead of Virtual Comport
#
import asyncio
import socket
from time import sleep

DEBUG = 0


#--------------------------------------------------------------------------------------------------
def get_ipv4():
    """
    Helper function that determines the own IPv4 address on the primary interface.
    Falls back to localhost if no IP available.

    Returns:
        str: IPv4 address
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

#--------------------------------------------------------------------------------------------------
async def send_msg(message: str):
    reader, writer = await asyncio.open_connection(UART_BRIDGE_IP, 23)
    if DEBUG:
        print(f'Send: {message!r} to 23')
    writer.write(message.encode())
    await writer.drain()
    if DEBUG:
        print('Close the SEND connection')
    writer.close()

#--------------------------------------------------------------------------------------------------
async def handle_echo(reader, writer):
    DEBUG = 1
    data = await reader.read(10)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    if DEBUG:
        print(f"Received {message!r} from {addr!r}")
    #await send_msg(message + " DU SACK!")
    #print(f"Send: {message!r}")
    #writer.write(data)
    #await writer.drain()
    if DEBUG:
        print("Close the RECEIVE connection")
    writer.close()

async def server_main(resource_string):
    """Start a server that can be connected by the ETH-to-UART bridge in TCP client mode."""

    if not resource_string:
        _IP = get_ipv4()
        _PORT = 8888
    else:
        _IP, _PORT = resource_string.split(":")

    server = await asyncio.start_server(handle_echo, _IP, _PORT)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    if DEBUG:
        print(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()

#--------------------------------------------------------------------------------------------------
async def tcp_send_and_receive_from_server(resource_string: str, message: str | None, timeout=1.0, limit: str | bytes | int = b'\n') -> str:
    """
    Connects to the ETH to UART bridge at the port 23 on the fixed IP UART_BRIDGE_IP.
    It sends some message if given and afterwards it waits for incoming with limit timeout.

    Args:
        message (str): message
        timeout (float, optional): Timeout for open, wait send and receive in seconds.
            timeout/2 is for open, rest for send/receive. Defaults to 1.0.
        limit (bytes, str or int, optional): Defines if the read function used:
            if limit is of bytes, it uses stream.readuntil(separator=limit)) so that the line
                termination can be set freely. Note that the terminator is stripped from data.
            if limit is of string, it uses stream.readline(). Note that the line terminator
                is NOT stripped from data.
            if limit is of integer, is uses stream.read(limit) so that the user can set the
                limit of bytes to be read. Note that at EOF the function returns even if less
                bytes than limit have been read.
            Defaults to b"\n".

    Returns:
        str: received data or None on timeout.
    """

    _IP, _PORT = resource_string.split(":")

    async def xchange(reader, writer):
        if message:
            if DEBUG:
                print(f'Send: {message!r}')
            writer.write(message.encode())
            await writer.drain()
        if isinstance(limit, int):
            #rcvdata = await reader.read()  # read until limit bytes or EOF
            rcvdata = bytes()
            while chunk := await reader.read(512):
                # read until limit bytes or EOF
                if not chunk:
                    break
                rcvdata += chunk
                if len(rcvdata) >= limit:
                    rcvdata = rcvdata[:limit]
                    break
        elif isinstance(limit, bytes):
            rcvdata = await reader.readuntil(separator=limit)  # read until \n or \r\n
        else:
            rcvdata = await reader.readline()  # read until \n or \r\n
        if DEBUG:
            print(f'Received: {rcvdata.decode()!r}')
        return rcvdata.decode()

    data = None
    # do NOT catch the exception for timeout here, propagate to the caller!
    #reader, writer = await asyncio.wait_for(asyncio.open_connection(_IP, _PORT), timeout/2)
    reader, writer = await asyncio.open_connection(_IP, _PORT)

    # Wait for at most 1 second (which is also the pause time for this loop)
    try:
        #data = await asyncio.wait_for(xchange(reader, writer), timeout)
        data = await xchange(reader, writer)
    except asyncio.exceptions.TimeoutError:
        pass
    finally:
        # Close the connection
        writer.close()
        await writer.wait_closed()

    return data


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    DEBUG = 1

    #UART_BRIDGE_IP = "192.168.1.120:2000"
    UART_BRIDGE_IP = "169.254.36.1:2000"

    # # test the client only:
    # i = 0
    # while True:
    #     i += 1
    #     print(i)
    #     #asyncio.run(tcp_send_and_receive_from_server(UART_BRIDGE_IP, 'Hello World!\r\n'))
    #     asyncio.run(tcp_send_and_receive_from_server(UART_BRIDGE_IP, None, timeout=10.0))

    # test the server method:
    # configure the 2nd socket at Waveshare as client to this server,
    # so we can get incoming data at any time (e.g. Barcodereader)
    asyncio.run(server_main("169.254.36.86:8888"))

# END OF FILE