# python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length
from enum import Enum
import sys
import select
import socket

 # Key is the client address, value is the packet(s) to send
snd_buff = {}

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

    def __init__(self, client_address):
        self._state = State.CLOSED
        self._ack = 0
        self._window = 0
        self._client_address = client_address
        # Initialize snd_buff as a queue of byte arrays
        snd_buff[self._client_address] = []

    def timeout(self):
        pass

    def create_packet(self, commands, seq_num=-1, ack_num=-1, window=-1, payload=""):
        '''
        Create a packet from the given components.
        '''
        packet = "|".join(commands) + "\n"
        packet += "Sequence: " + str(seq_num) + "\n"
        packet += "Length: " + str(len(payload)) + "\n"
        packet += "Acknowledgement: " + str(ack_num) + "\n"
        packet += "Window: " + str(window) + "\n"
        packet += "\n" + payload

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
                self._state = State.SYN_SENT
        elif self._state == State.SYN_RCVD:
            if "SYN" in commands:
                self._state = State.SYN_SENT
        elif self._state == State.FIN_RCVD:
            if "FIN" in commands:
                self._state = State.FIN_SENT
        elif self._state == State.CONNECTED:
            if "FIN" in commands:
                self._state = State.FIN_SENT
        elif self._state == State.FIN_SENT:
            if "ACK" in commands:
                self._state = State.CLOSED

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)
        print(commands, seq_num, length, ack_num, window, payload)

        if self._state == State.CLOSED:
            if "SYN" in commands:
                self._state = State.SYN_RCVD
        elif self._state == State.SYN_RCVD:
            if "FIN" in commands:
                self._state = State.FIN_RCVD
        elif self._state == State.SYN_SENT:
            if "ACK" in commands:
                self._state = State.CONNECTED
        elif self._state == State.CONNECTED:
            if "FIN" in commands:
                self._state = State.CON_FIN_RCVD

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

    print("Server IP address: " + server_ip_address)
    print("Server UDP port number: " + str(server_udp_port_number))
    print("Server buffer size: " + str(server_buffer_size))
    print("Server payload length: " + str(server_payload_length))

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
                clients[client_address] = RDP(client_address)
            clients[client_address].receive_packet(message)

            print("Server received message from " + str(client_address) + ": " + message.decode())

        if udp_sock in writable:
            for c in clients:
                msg = f"Hello from server to {c}"
                udp_sock.sendto(msg.encode(), c)


        if udp_sock in exceptional:
            pass

if __name__ == "__main__":
    main()