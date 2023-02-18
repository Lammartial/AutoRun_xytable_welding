import asyncio, socket
from rrc.eth2serial.base_async import get_ipv4, tcp_send_and_receive_from_server

async def handle_client(reader, writer):
    print("Listen on:", get_ipv4())
    request = None
    while request != 'quit':
        request = (await reader.read(255)).decode('utf8')
        #response = str(eval(request)) + '\n'
        #writer.write(response.encode('utf8'))
        #await writer.drain()
        print(request)
    writer.close()

async def run_server():
    #server = await asyncio.start_server(handle_client, '169.254.36.86', 8888)
    #server = await asyncio.start_server(handle_client, host='0.0.0.0', port=8888)
    #async with server:
    #    await server.serve_forever()
    pass

asyncio.run(run_server())