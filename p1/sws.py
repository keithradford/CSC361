import socket
import select
import sys
import queue
import re
from datetime import datetime, timedelta
from os.path import exists

EOL_PATTERN = r'^(\r\n|\n)[2]$'
TERMINAL_EOR_PATTERN = r'^(\r\n|\n)?$'
EOR_PATTERN = r'.*(\r\n\r\n|\n\n)$'
REQ_PATTERN = r'^GET\s\/(.*)\sHTTP\/1.0(\r\n|\n)?'
CONNECTION_PATTERN = r'Connection:\s?(.*)\s*(\r\n|\n)?'
TIMEOUT = 60.0

ip_address = sys.argv[1]
port_number = int(sys.argv[2])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)
server.bind((ip_address, port_number))
server.listen(5)

inputs = [server]
outputs = []
response_messages = {}
request_message = {}
close_connection = {}
last_event = {}

def main():
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs, TIMEOUT)

        if not (readable or writable or exceptional):
            for socket in inputs:
                if socket != server:
                    if check_timeout(socket):
                        handle_connection_error(socket)
            continue

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

def check_timeout(socket):
    if last_event[socket] + timedelta(seconds=TIMEOUT) < datetime.now():
        return True

def check_format(message):
    if re.match(REQ_PATTERN, message) or re.match(CONNECTION_PATTERN, message) or re.match(EOL_PATTERN, message):
        return True
    return False

def handle_new_connection(socket):
    connection, _ = socket.accept()
    connection.setblocking(0)
    inputs.append(connection)
    response_messages[connection] = queue.Queue()
    close_connection[connection] = True
    last_event[connection] = datetime.now()

def handle_existing_connection(socket):
    message = socket.recv(1024).decode()
    last_event[socket] = datetime.now()
    if message:
        if request_message.get(socket) is None:
            request_message[socket] = message
        else:
            request_message[socket] += message
        if re.search(EOR_PATTERN, message) or re.match(TERMINAL_EOR_PATTERN, message):
            whole_message = request_message[socket]
            outputs.append(socket)

            req_file = ""
            file_found = False
            bad_request = False
            connection_header = False
            i = 0

            requests = list(filter((lambda x: x != "\r\n\r\n" and x != "\n\n" and x != ""), re.split(r'(\r\n\r\n|\n\n)', whole_message)))
            responses = []

            for request in requests:
                log = {"response": "", "request": "", "time": datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")}
                for line in request.splitlines():
                    if not check_format(line):
                        if i < len(responses) - 1:
                            responses[i] = "HTTP/1.0 400 Bad Request\r\n\r\n"
                        else:
                            responses.append("HTTP/1.0 400 Bad Request\r\n\r\n")
                        log["response"] = "HTTP/1.0 400 Bad Request"
                        if not log["request"]:
                            log["request"] = line.strip()
                        bad_request = True
                    else:
                        if re.match(REQ_PATTERN, line):
                            log["request"] = line.strip()
                            req_file = re.match(REQ_PATTERN, line).group(1) if re.match(REQ_PATTERN, line).group(1) != "" else "index.html"
                            if exists(req_file):
                                responses.append("HTTP/1.0 200 OK\r\n")
                                log["response"] = "HTTP/1.0 200 OK"
                                file_found = True
                            else:
                                responses.append("HTTP/1.0 404 Not Found\r\n")
                                log["response"] = "HTTP/1.0 404 Not Found"
                        elif re.match(CONNECTION_PATTERN, line):
                            connection_header = True
                            connection = re.search(CONNECTION_PATTERN, line).group(1)
                            if connection.lower() == "keep-alive":
                                close_connection[socket] = False
                            elif connection.lower() == "close":
                                close_connection[socket] = True
                print(f"{log['time']}: {socket.getpeername()[0]}:{port_number} {log['request']}; {log['response']}")
                c = "close" if close_connection[socket] or not connection_header else "keep-alive"
                responses[i] += f"Connection: {c}\r\n\r\n" if not bad_request else ""
                if file_found:
                    with open(req_file, 'r') as f:
                        responses[i] += f.read()
                    responses[i] += "\r\n\r\n"
                if close_connection[socket] or not connection_header:
                    close_connection[socket] = True
                    break
                file_found = False
                bad_request = False
                req_file = ""
                i += 1
                connection_header = False
                request_message[socket] = ""
            for response in responses:
                response_messages[socket].put(response)

def write_back_response(socket):
    try:
        next_msg = response_messages[socket].get_nowait()

    except queue.Empty:
        outputs.remove(socket)
    else:
        msg = next_msg.encode()
        socket.send(msg)
        last_event[socket] = datetime.now()
        if(close_connection[socket] and response_messages[socket].empty()):
            outputs.remove(socket)
            inputs.remove(socket)
            last_event.pop(socket)
            socket.close()

def handle_connection_error(socket):
    if socket in outputs:
        outputs.remove(socket)
    inputs.remove(socket)
    socket.close()

# --------------- End of helper methods ----------------

if __name__ == "__main__":
    main()
