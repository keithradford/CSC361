# Reliable Datagram Protocol
from datetime import datetime
import socket
import select
import sys
import queue
from enum import Enum

if len(sys.argv) != 5:
    print("Usage: python3 rdp.py <ip_address> <local_port> <read_file_name> <write_file_name>")
    sys.exit(1)

ip_address = sys.argv[1]
port_number = int(sys.argv[2])
read_file_name = sys.argv[3]
write_file_name = sys.argv[4]

# pipe file into string that i can keep track of using ACK, SEQ numbers

# Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Initialize a queue for the sending buffer
snd_buff = bytearray(1024)

# Initialize the receiving buffer
rcv_buff = bytearray(2048)

# Packet format
# CMD
# Header: value
# Header: value
#
# PAYLOAD
def create_packet(command, seq_num=-1, ack_num=-1, payload=None, window=-1):
    packet = f"{command}\r\n"
    if seq_num != -1:
        packet += f"Sequence: {seq_num}\r\n"
    if ack_num != -1:
        packet += f"Acknowledgment: {ack_num}\r\n"
    if window != -1:
        packet += f"Window: {window}\r\n\r\n"
    if payload is not None:
        packet += f"Length: {len(payload)}\r\n\r\n"
        packet += f"{payload}\r\n"
    elif window == -1:
        packet += "Length: 0\r\n\r\n"

    return packet

def send_packet(packet):
    bytes_sent = udp_sock.sendto(packet, (ip_address, 8888))
    return bytes_sent

def log(command, send=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if send:
        print(f"{time}: Send; {command}; Sequence: {seq_num}; Length: {length}")
    else:
        print(f"{time}: Receive; {command}; Acknowledgement: {ack_num}; Window: {window}")

def write_to_byte_array(byte_array, data, offset=0):
    for i in range(len(data)):
        curr = data[i] if type(data[i]) is int else ord(data[i])
        byte_array[offset + i] = curr

def parse_packet(packet):
    lines = packet.decode("utf-8").split("\r\n")
    command = lines[0]
    seq_num = -1
    ack_num = -1
    payload = None
    for line in lines:
        if line.startswith("Sequence"):
            seq_num = int(line.split(": ")[1])
        elif line.startswith("Acknowledgment"):
            ack_num = int(line.split(": ")[1])
        elif line.startswith("Length"):
            payload = lines[-1]

    return command, seq_num, ack_num, payload

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    OPEN = 2
    FIN_SENT = 3

class rdp_sender:
    def __init__(self):
        self._state = State.CLOSED

    def _send(self):
        if self._state == State.SYN_SENT:
            print ("Sending SYN")
            packet = create_packet("SYN", 0)
            write_to_byte_array(snd_buff, packet)
        if self._state == State.OPEN:
            print ("Sending data")
            packet = create_packet("DAT", 1, payload="Hello")
            write_to_byte_array(snd_buff, packet)

    def open(self):
        self._state = State.SYN_SENT
        self._send()

    def receive_ack(self, ack):
        print("Received ACK")
        if self._state == State.SYN_SENT:
            self._state = State.OPEN
            self._send()

    def timeout(self):
        pass

    def close(self):
        pass

    def get_state(self):
        return self._state

class rdp_receiver:
    def __init__(self):
        self._state = State.CLOSED
        self.window = 2048

    def send(self, data):
        pass

    def receive(self):
        pass

    def open(self):
        pass

    def receive_data(self, data):
        print("Receiver received data")
        _, seq_num, __, ___ = parse_packet(data)
        packet = create_packet("ACK", ack_num=seq_num + 1, window=1024)
        print(packet)
        send_packet(packet.encode())

    def get_state(self):
        return self._state

def main():
    sender = rdp_sender()
    receiver = rdp_receiver()
    sender.open()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        print("readable", readable)
        print("writable", writable)
        print("exceptional", exceptional)

        if udp_sock in readable:
            message, _ = udp_sock.recvfrom(8192)
            write_to_byte_array(rcv_buff, message)
            command, _, __, ___ = parse_packet(message)
            print("Received", command)
            if command == "ACK":
                sender.receive_ack(message)
            else:
                receiver.receive_data(message)

        if udp_sock in writable:
            send_packet(snd_buff)

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()