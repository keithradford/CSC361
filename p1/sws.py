from math import nextafter
import socket
import select
import sys
import queue
import re
from datetime import datetime
from os.path import exists

EOL_PATTERN = r'^(\r\n|\n)?$'
REQ_PATTERN = r'^GET\s\/(.*)\sHTTP\/1.0(\r\n|\n)?'
CONNECTION_PATTERN = r'Connection:\s?(.*)\s*(\r\n|\n)?'

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
close_connection = {}
log = {"response": "", "request": "", "time": ""}

def main():
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for s in readable:
            if s is server:
                handle_new_connection(s)
            else:
                handle_existing_connection(s)

        for s in writable:
            write_back_response(s)

        for s in exceptional:
            handle_connection_error(s)

# --------------- Helper methods ----------------

def check_format(message):
    if re.match(REQ_PATTERN, message) or re.match(CONNECTION_PATTERN, message) or re.match(EOL_PATTERN, message):
        return True
    return False

def handle_new_connection(socket):
    connection, client_address = socket.accept()
    print("Connection from", client_address)
    connection.setblocking(0)
    inputs.append(connection)
    response_messages[connection] = queue.Queue()
    close_connection[connection] = True

def handle_existing_connection(socket):
    message = socket.recv(1024).decode()
    if message:
        if request_message.get(socket) is None:
            request_message[socket] = message
        else:
            request_message[socket] += message
        if re.match(EOL_PATTERN, message):
            whole_message = request_message[socket]
            log["request"] = whole_message.strip()
            outputs.append(socket)

            req_file = ""
            connection = "close"
            file_found = False

            for line in whole_message.splitlines():
                if not check_format(line):
                    # Clear existing response messages
                    response_messages[socket].queue.clear()
                    response_messages[socket].put("HTTP/1.0 400 Bad Request\r\n\r\n")
                    log["response"] = "HTTP/1.0 400 Bad Request"
                    close_connection[socket] = True
                    break
                else:
                    if re.match(REQ_PATTERN, line):
                        req_file = re.match(REQ_PATTERN, line).group(1) if re.match(REQ_PATTERN, line).group(1) != "" else "index.html"
                        if exists(req_file):
                            response_messages[socket].put("HTTP/1.0 200 OK\r\n")
                            log["response"] = "HTTP/1.0 200 OK"
                            file_found = True
                        else:
                            response_messages[socket].put("HTTP/1.0 404 Not Found\r\n")
                            log["response"] = "HTTP/1.0 404 Not Found"
                    elif re.match(CONNECTION_PATTERN, line):
                        connection = re.search(CONNECTION_PATTERN, line).group(1)
                        if connection == "keep-alive":
                            close_connection[socket] = False
            response_messages[socket].put(f"Connection: {connection}\r\n\r\n")
            if file_found:
                with open(req_file, 'r') as f:
                    response_messages[socket].put(f.read())
                response_messages[socket].put("\r\n")

def write_back_response(socket):
    try:
        next_msg = response_messages[socket].get_nowait()
    except queue.Empty:
        outputs.remove(socket)
    else:
        msg = next_msg.encode()
        socket.send(msg)
        if(close_connection[socket] and response_messages[socket].empty()):
            log["time"] = datetime.now().strftime('%A %d-%m-%Y, %H:%M:%S')
            print(f"{log['time']}: {ip_address}:{port_number} {log['request']}; {log['response']}")
            outputs.remove(socket)
            inputs.remove(socket)
            socket.close()

def handle_connection_error(socket):
    print("Connection error")
    if socket in outputs:
        outputs.remove(socket)
    inputs.remove(socket)
    socket.close()

# --------------- End of helper methods ----------------

if __name__ == "__main__":
    main()