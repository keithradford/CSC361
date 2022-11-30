"""
python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*
If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection
"""

import sys
import socket
import select
from enum import Enum

server_ip_address = sys.argv[1]
server_udp_port_number = int(sys.argv[2])
client_buffer_size = int(sys.argv[3])
client_payload_length = int(sys.argv[4])
read_file_name = sys.argv[5]
write_file_name = sys.argv[6]

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    SYN_RCVD = 2
    CONNECTED = 3
    FIN_SENT = 4
    FIN_RCVD = 5
    CON_FIN_RCVD = 6

buff = []

def process_response(response):
    '''
    Processes a HTTP response and returns the payload
    '''
    lines = response.splitlines()
    payload = ""
    for line in lines:
        if line.startswith("HTTP") or line.startswith("Connection") or line.startswith("Content-Length"):
            continue
        payload += line

    return payload

class RDP:
    '''
    The sender of the reliable data transfer protocol
    '''

    def __init__(self, window):
        self._state = State.CLOSED
        self._seq = 0
        self._window = window
        self._data = ""
        self._ack = 0

        # Create initial HTTP request
        request = "GET /" + read_file_name + " HTTP/1.0\r\n"
        request += "Connection: keep-alive\r\n"
        self.send_packet(["SYN", "ACK", "DAT"], 0, -1, self._window, request)

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
                print("Going from CLOSED to SYN_SENT")
                self._state = State.SYN_SENT
        if self._state == State.SYN_RCVD:
            if "SYN" in commands:
                print("Going from SYN_RCVD to CONNECTED")
                self._state = State.SYN_SENT
        if self._state == State.FIN_RCVD:
            if "FIN" in commands:
                print("Going from FIN_RCVD to CLOSED")
                self._state = State.FIN_SENT
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                print("Going from CONNECTED to FIN_SENT")
                self._state = State.FIN_SENT
        if self._state == State.CON_FIN_RCVD:
            if "FIN" in commands:
                print("Going from CON_FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT

        packet = self.create_packet(commands, seq_num, ack_num, window, payload)
        buff.append(packet)

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)
        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1

        # TODO: Handle DAT, detect correct ACK, send FINs
        if "DAT" in commands:
            self._data += process_response(payload.strip())
        send_commands = []
        if self._state == State.CLOSED:
            if "SYN" in commands:
                print("Going from CLOSED to SYN_RCVD")
                send_commands.append("SYN")
                self._state = State.SYN_RCVD
        if self._state == State.SYN_RCVD:
            if "FIN" in commands:
                print("Going from SYN_RCVD to FIN_RCVD")
                self._state = State.FIN_RCVD
        if self._state == State.SYN_SENT:
            if "ACK" in commands:
                print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
                send_commands.append("FIN")

        # Send packet for first chunk of data
        self.send_packet(send_commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[:self._window])
        # Send packets for remaining data
        for i in range(self._window, len(self._data), self._window):
            self.send_packet(["DAT", "ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[i:i+self._window])

        if self._state == State.FIN_SENT:
            if "ACK" in commands:
                print("Going from FIN_SENT to CLOSED")
                self._state = State.CLOSED
                # Write data to file
                with open(write_file_name, "w") as f:
                    f.write(self._data)
                # TODO: Replace this with timeout
                sys.exit(0)


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
    if len(sys.argv) < 7 or len(sys.argv) % 2 != 1:
        print("Usage: python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*")
        print("* If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection")
        sys.exit(1)

    # Initialize UDP socket and bind to server IP address and port number
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    rdp = RDP(client_payload_length)

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(client_buffer_size)
            print("Client received message from " + str(client_address) + ": " + message.decode())
            rdp.receive_packet(message)

        if udp_sock in writable:
            if buff:
                packet = buff.pop(0)
                print("Client sending message to " + str((server_ip_address, server_udp_port_number)) + ": " + packet.decode())
                udp_sock.sendto(packet, (server_ip_address, server_udp_port_number))

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()