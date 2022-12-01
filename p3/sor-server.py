# python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length
from enum import Enum
import sys
import select
import socket
import re
from datetime import datetime

# Parse arguments
server_ip_address = sys.argv[1]
server_udp_port_number = int(sys.argv[2])
server_buffer_size = int(sys.argv[3])
server_payload_length = int(sys.argv[4])

 # Key is the client address, value is the packet(s) to send
buff = {}
acked = {}
timer = {}

REQUEST_PATTERN = r"^GET\s\/(.*)\sHTTP\/1.0((\r\n|\n)Connection:\s(keep-alive|close))?$"

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    SYN_RCVD = 2
    CONNECTED = 3
    FIN_SENT = 4
    FIN_RCVD = 5
    CON_FIN_RCVD = 6

class RDP:
    '''
    The sender of the reliable data transfer protocol
    '''

    def __init__(self, client_address, window):
        self._state = State.CLOSED
        self._seq = 0
        self._window = window
        self._client_address = client_address
        self._data = None
        self._ack = 0

        # Initialize buff as a queue of byte arrays
        buff[self._client_address] = [b""] * window
        acked[self._client_address] = [False] * window
        timer[self._client_address] = [None] * window

    def process_request(self, request):
        '''
        Processes a HTTP request and returns a response
        '''
        response = ""
        # Check for valid request
        if not re.match(REQUEST_PATTERN, request):
            response = self.create_response(400, "close")
        lines = request.splitlines()
        payload = ""
        keep_alive = False
        for line in lines:
            if line.startswith("GET"):
                # Read the file in REGEX group 1
                filename = re.search(REQUEST_PATTERN, request).group(1)
                try:
                    with open(filename, "r") as f:
                        payload = f.read()
                except FileNotFoundError:
                    response = self.create_response("404", "close")
                break
            if line.startswith("Connection"):
                # Check if connection is closed
                if re.search(REQUEST_PATTERN, request).group(4) == "keep-alive":
                    keep_alive = True

        response = self.create_response("200", "keep-alive" if keep_alive else "close", payload)
        self.log(lines[0], response.splitlines()[0])

        return response

    def create_response(self, status_code, connection, payload=None):
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

    def log(self, request, response):
        '''
        Logs the current time, client, request, and response to the console
        '''
        now = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
        print(f"{now}: {self._client_address[0]}:{self._client_address[1]}: {request}; {response}")

    def timeout(self):
        pass

    def create_packet(self, commands, seq_num=-1, ack_num=-1, window=-1, payload=""):
        '''
        Create a packet from the given components.
        '''
        payload_length = len(payload) if payload else 0
        packet = "|".join(commands) + "\n"
        packet += "Sequence: " + str(seq_num) + "\n"
        packet += "Length: " + str(payload_length) + "\n"
        packet += "Acknowledgement: " + str(ack_num) + "\n"
        packet += "Window: " + str(window) + "\n"
        packet += "\n" + payload if payload else ""

        return packet.encode()

    def parse_packet(self, packet):
        '''
        Parse a packet into its components.
        '''

        lines = packet.decode().splitlines()
        commands = lines[0].split("|")
        # Sequence: #
        seq_num = int(lines[1].split(": ")[1])
        # Length: #
        length = int(lines[2].split(": ")[1])
        # Acknowledgement: #
        ack_num = int(lines[3].split(": ")[1])
        # Window: #
        window = int(lines[4].split(": ")[1])
        # Payload = remaining lines
        payload = "\n".join(lines[5:])

        return commands, seq_num, length, ack_num, window, payload

    def send_packet(self, commands, seq_num=-1, ack_num=-1, window=-1, payload=""):
        if self._state == State.CLOSED:
            if "SYN" in commands:
                # print("Going from CLOSED to SYN_SENT")
                self._state = State.SYN_SENT
        if self._state == State.SYN_RCVD:
            if "SYN" in commands:
                # print("Going from SYN_RCVD to SYN_SENT")
                self._state = State.SYN_SENT
        if self._state == State.FIN_RCVD:
            if "FIN" in commands:
                # print("Going from FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to FIN_SENT")
                self._state = State.FIN_SENT
        if self._state == State.CON_FIN_RCVD:
            if "FIN" in commands:
                # print("Going from CON_FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT

        packet = self.create_packet(commands, seq_num, ack_num, window, payload)
        # print(f"Sending packet: {packet}")
        buff[self._client_address][seq_num % server_buffer_size] = packet

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)
        # print(commands)
        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1
        # self._window = server_buffer_size

        # TODO: Handle DAT, detect correct ACK, send FINs

        send_commands = []
        if self._state == State.CLOSED:
            if "SYN" in commands:
                # print("Going from CLOSED to SYN_RCVD")
                send_commands.append("SYN")
                self._state = State.SYN_RCVD
            if "DAT" in commands:
                send_commands.append("DAT")
                self._data = self.process_request(payload.strip())
        if self._state == State.SYN_RCVD:
            if "FIN" in commands:
                # print("Going from SYN_RCVD to FIN_RCVD")
                self._state = State.FIN_RCVD
        if self._state == State.SYN_SENT:
            if "ACK" in commands:
                # print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
            if "DAT" in commands:
                send_commands.append("DAT")
                self._data = self.process_request(payload.strip())
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
                send_commands.append("FIN")
            if "DAT" in commands:
                send_commands.append("DAT")
                self._data = self.process_request(payload.strip())

        if self._state == State.FIN_SENT:
            if "ACK" in commands and "FIN" in commands:
                self.send_packet(["ACK"], self._seq, self._ack)
            else:
                # print("Going from FIN_SENT to CLOSED")
                self._state = State.CLOSED

        print("self._data", len(self._data), self._state)
        if "DAT" in send_commands:
            # Send packet for first chunk of data
            # self.send_packet(send_commands + ["ACK"] + ["FIN"] if len(self._data) < self._window else [], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[:server_payload_length])
            # new_state = State.FIN_SENT if len(self._data) < self._window else self._state
            # self._window -= server_payload_length
            # # print(f"Going from {self._state} to {new_state}")
            # self._state = new_state
            # Send packets for data that fits in window
            # i = seq_num
            while self._window > 0:
                self.send_packet(send_commands + ["ACK"] + ["FIN"] if len(self._data) < self._window else [], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[:server_payload_length])
                # If it's the last packet, break
                if len(self._data) < self._window:
                    self._state = State.FIN_SENT
                    self._window -= len(self._data)
                self._window -= server_payload_length
                self._data = self._data[server_payload_length:]
                # print(f"Going from {self._state} to {new_state}")
            # for i in range(self._window, len(self._data), self._window):
            #     # Send FIN if this is the last packet
            #     if i + self._window >= len(self._data):
            #         self.send_packet(["DAT", "ACK", "FIN"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[i:i+self._window])
            #         # print(f"Going from {self._state} to FIN_SENT")
            #         self._state = State.FIN_SENT
            #     else:
            #         self.send_packet(["DAT", "ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[i:i+self._window])
        else:
            self.send_packet(send_commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window)


    def package_data(self, data):
        '''
        Package data into packets of size <= window
        '''
        packets = []
        pointer = 0
        while pointer < len(data):
            packets.append(data[pointer:pointer+self._window])
            pointer += self._window

        return packets

def main():
    # Check for correct number of arguments
    if len(sys.argv) != 5:
        print("Usage: python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length")
        sys.exit(1)

    # Initialize UDP socket and bind to server IP address and port number
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((server_ip_address, server_udp_port_number))

    # Key is the client address, value is an RDP instance
    clients = {}

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(server_buffer_size)

            if client_address not in clients:
                clients[client_address] = RDP(client_address, server_buffer_size)
            clients[client_address].receive_packet(message)

        if udp_sock in writable:
            for c in buff:
                for i in range(len(buff[c])):
                    packet = buff[c][i]
                    if(packet):
                        print("Sending packet to client", packet.decode())
                        udp_sock.sendto(packet, c)
                        buff[c][i] = b""



        if udp_sock in exceptional:
            pass

if __name__ == "__main__":
    main()