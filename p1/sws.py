import socket
import select
import sys
import queue
import time
import re

EOL_PATTERN = r'.*(\r\n\r\n|\n\n)$'
REQ_PATTERN = r'^GET (.*) HTTP\/1.0(\r\n|\n)'
CONNECTION_PATTERN = r'Connection: (.*)'

ip_address = sys.argv[1]
port_number = int(sys.argv[2])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Socket created")

server.setblocking(0)

server.bind((ip_address, port_number))
print("Socket binded to %s" %(port_number))

server.listen(5)
print("Socket is listening")

# Sockets to watch for readability
inputs = [server]
# Sockets to watch for writability
outputs = []
# Outgoing message queues (socket:Queue)
response_messages = {}
# request message
request_message = {}

while True:
    readable, _, __ = select.select(inputs, outputs, inputs)

    for s in readable:
        if s is server:
            connection, client_address = s.accept()
            print("Connection from", client_address)
            connection.setblocking(0)
            inputs.append(connection)
            response_messages[connection] = queue.Queue()
        else:
            message = s.recv(1024).decode()
            if message:
                print("Received message from client:", message)
                if request_message.get(s) is None:
                    request_message[s] = message
                else:
                    request_message[s] += message
                if re.match(EOL_PATTERN, request_message[s]):
                    print("success")
                    whole_message = request_message[s]

                    outputs.append(s)
                    # for line in whole_message.splitlines():
                        # if format is incorrect
                        # else
                        # add response
    for s in outputs:
        try:
            next_msg = response_messages[s].get_nowait()
        except queue.Empty:
            outputs.remove(s)
        else:
            s.send(next_msg.encode())