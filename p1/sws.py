import socket
import select
import sys
import queue
import time
import re
from os.path import exists

EOL_PATTERN = r'^(\r\n|\n)?$'
REQ_PATTERN = r'^GET\s\/(.*)\sHTTP\/1.0(\r\n|\n)?'
CONNECTION_PATTERN = r'Connection:\s(.*)(\r\n|\n)?'

ip_address = sys.argv[1]
port_number = int(sys.argv[2])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Socket created")

server.setblocking(0)

server.bind((ip_address, port_number))
print("Socket binded to %s" %(port_number))

server.listen(5)
print("Socket is listening")

inputs = [server]
outputs = []
response_messages = {}
request_message = {}

def check_format(message):
    if re.match(REQ_PATTERN, message) or re.match(CONNECTION_PATTERN, message) or re.match(EOL_PATTERN, message):
        return True
    return False

def print_queue(queue):
    while not queue.empty():
        print(queue.get())

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
                if request_message.get(s) is None:
                    request_message[s] = message
                else:
                    request_message[s] += message
                if re.match(EOL_PATTERN, message):
                    whole_message = request_message[s]
                    outputs.append(s)

                    req_file = "/"
                    file_found = False

                    for line in whole_message.splitlines():
                        if not check_format(line):
                            # Clear existing response messages
                            response_messages[s].queue.clear()
                            response_messages[s].put("HTTP/1.0 400 Bad Request\r\n\r\n")
                            break
                        else:
                            if re.match(REQ_PATTERN, line):
                                req_file = re.match(REQ_PATTERN, line).group(1) if re.match(REQ_PATTERN, line).group(1) != "/" else "index.html"
                                print("req_file: ", req_file)
                                if exists(req_file):
                                    response_messages[s].put("HTTP/1.0 200 OK\r\n")
                                    file_found = True
                                else:
                                    response_messages[s].put("HTTP/1.0 404 Not Found\r\n")
                            elif re.match(CONNECTION_PATTERN, line):
                                result = re.search(CONNECTION_PATTERN, line)
                                response_messages[s].put(f"Connection: {result.group(1)}\r\n\r\n")
                    if file_found:
                        with open(req_file, 'r') as f:
                            response_messages[s].put(f.read())
                        print('\r\n')

    for s in outputs:
        try:
            next_msg = response_messages[s].get_nowait()
        except queue.Empty:
            outputs.remove(s)
        else:
            s.send(next_msg.encode())