# python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length
import sys
import select
import socket
from rdp import RDP
import re
from datetime import datetime


def process_request(request, client_address):
    '''
    Processes a HTTP request and returns a response
    '''

    request_pattern = r"^GET\s\/(.*)\sHTTP\/1.0((\r\n|\n)Connection:\s(keep-alive|close))?$"
    response = ""
    # Check for valid request
    if not re.match(request_pattern, request):
        response = create_response(400, "close")
        log(request, response.splitlines()[0], client_address)

        return response
    lines = request.splitlines()
    payload = ""
    keep_alive = False
    for line in lines:
        if line.startswith("GET"):
            # Read the file in REGEX group 1
            filename = re.search(request_pattern, request).group(1)
            try:
                with open(filename, "r") as f:
                    payload = f.read()
            except FileNotFoundError:
                response = create_response("404", "close")
                log(lines[0], response.splitlines()[0], client_address)

                return response
            break
        if line.startswith("Connection"):
            # Check if connection is closed
            if re.search(request_pattern, request).group(4) == "keep-alive":
                keep_alive = True

    response = create_response("200", "keep-alive" if keep_alive else "close", payload)
    log(lines[0], response.splitlines()[0], client_address)

    return response

def create_response(status_code, connection, payload=None):
    '''
    Creates a HTTP response given a status code and payload
    '''
    status = "200 OK" if status_code == "200" else "404 Not Found" if status_code == "404" else "400 Bad Request"
    response = f"HTTP/1.0 {status}\r\n"
    response += f"Connection: {connection}\r\n"
    if payload:
        response += f"Content-Length: {len(payload)}\r\n"
        response += f"\r\n{payload}" if payload else "\r\n"

    return response

def log(request, response, client_address):
    '''
    Logs the current time, client, request, and response to the console
    '''
    now = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    print(f"{now}: {client_address[0]}:{client_address[1]}: {request}; {response}")

def main():
    # Check for correct number of arguments
    if len(sys.argv) != 5:
        print("Usage: python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length")
        sys.exit(1)

    # Parse arguments
    server_ip_address = sys.argv[1]
    server_udp_port_number = int(sys.argv[2])
    server_buffer_size = int(sys.argv[3])
    server_payload_length = int(sys.argv[4])

    # Initialize UDP socket and bind to server IP address and port number
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((server_ip_address, server_udp_port_number))

    # Key is the client address, value is an RDP instance
    clients = {}
    # Key is the client address, value is DAT to send
    active = {}

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(server_payload_length)

            if client_address not in clients:
                clients[client_address] = RDP(server_buffer_size, server_payload_length)
                active[client_address] = True
            payload = clients[client_address].receive_packet(message)
            if payload:
                response = process_request(payload.strip(), client_address)
                # print("Response: ", response)
                clients[client_address].add_data(response)
                active[client_address] = True

        if udp_sock in writable:
            for c in clients:
                if active[c]:
                    packets = clients[c].send_packet()
                    # If RST packet is received, close connection
                    for p in packets:
                        if b"RST" in p:
                            udp_sock.sendto(p, c)
                            active[c] = False
                            break
                        udp_sock.sendto(p, c)

        if udp_sock in exceptional:
            pass

if __name__ == "__main__":
    main()
