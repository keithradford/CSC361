# Reliable Datagram Protocol
from datetime import datetime
import socket
import select
import sys
from enum import Enum

if len(sys.argv) != 5:
    print("Usage: python3 rdp.py <ip_address> <local_port> <read_file_name> <write_file_name>")
    sys.exit(1)

ip_address = sys.argv[1]
port_number = int(sys.argv[2])
read_file_name = sys.argv[3]
write_file_name = sys.argv[4]

# pipe file into string that i can keep track of using ACK, SEQ numbers

# Read file into string
file_data = ""
with open(read_file_name, "r") as f:
    file_data += f.read()

# Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Initialize a queue for the sending buffer
snd_buff = bytearray(2048)

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

def send_packet(packet, sender=True):
    command, seq_num, ack_num, window, payload = parse_packet(packet)
    send_log(command, sender, seq_num, len(payload if payload else ""), ack_num, window)
    bytes_sent = udp_sock.sendto(packet, (ip_address, 8888))
    return bytes_sent

def receive_log(command, sender=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if sender:
        print(f"{time}: Receive; {command}; Acknowledgement: {ack_num}; Window: {window}")
    else:
        print(f"{time}: Receive; {command}; Sequence: {seq_num}; Length: {length}")

def send_log(command, sender=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if sender:
        print(f"{time}: Send; {command}; Sequence: {seq_num}; Length: {length}")
    else:
        print(f"{time}: Send; {command}; Acknowledgement: {ack_num}; Window: {window}")

def write_to_byte_array(byte_array, data, offset=0):
    for i in range(len(data)):
        curr = data[i] if type(data[i]) is int else ord(data[i])
        byte_array[offset + i] = curr

def parse_packet(packet):
    lines = packet.decode("utf-8").split("\r\n")
    command = lines[0]
    seq_num = -1
    ack_num = -1
    window = -1
    payload = None
    for line in lines:
        if line.startswith("Sequence"):
            seq_num = int(line.split(": ")[1])
        elif line.startswith("Acknowledgment"):
            ack_num = int(line.split(": ")[1])
        elif line.startswith("Window"):
            window = int(line.split(": ")[1])
        elif line.startswith("Length"):
            payload = lines[-2]

    return command, seq_num, ack_num, window, payload

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    OPEN = 2
    FIN_SENT = 3

class rdp_sender:
    def __init__(self):
        self._state = State.CLOSED
        self._ack = 0
        self._window = 0

    def _send(self):
        if self._state == State.SYN_SENT:
            packet = create_packet("SYN", 0)
            write_to_byte_array(snd_buff, packet)
        if self._state == State.OPEN:
            # If all the data has been sent, close
            if self._ack >= len(file_data):
                self.close()

            max_send = min(self._window, 1024)
            # Get the next max_send bytes of data
            payload = file_data[(self._ack - 1):self._ack + max_send - 1]
            packet = create_packet("DAT", self._ack, payload=payload)
            write_to_byte_array(snd_buff, packet)
        if self._state == State.FIN_SENT:
            packet = create_packet("FIN", self._ack)
            write_to_byte_array(snd_buff, packet)

    def open(self):
        self._state = State.SYN_SENT
        self._send()

    def receive_ack(self, ack):
        # Parse ack
        command, seq_num, ack_num, window, payload = parse_packet(ack)
        receive_log(command, True, ack_num=ack_num, window=window)
        self._ack = ack_num
        self._window = window
        if self._state == State.SYN_SENT:
            self._state = State.OPEN
            self._send()
        if self._state == State.FIN_SENT:
            self._state = State.CLOSED
            exit(0)
        if self._state == State.OPEN:
            self._send()

    def timeout(self):
        pass

    def close(self):
        self._state = State.FIN_SENT
        self._send()

    def get_state(self):
        return self._state

class rdp_receiver:
    def __init__(self):
        self._window = 2048
        self._rcv_buff = ""

    def receive_data(self, data):
        command, seq_num, ack_num, window, payload = parse_packet(data)
        receive_log(command, False, seq_num=seq_num, length=len(payload))
        # Decrease the window
        self._window -= len(payload)
        # If the window is 0, empty the buffer to file
        if self._window == 0 and len(payload) > 0 or command == "FIN":
            # Write to file
            with open(write_file_name, "a") as f:
                # f.write("NEW CHUNK")
                f.write(self._rcv_buff)
            # Reset the buffer and window
            self._rcv_buff = ""
            self._window = 2048
        if len(payload) > 0:
            # Add to buffer
            self._rcv_buff += payload
        padding = len(payload) - 1 if len(payload) > 0 else 0
        packet = create_packet("ACK", ack_num=seq_num + padding + 1, window=self._window)
        send_packet(packet.encode(), False)

def main():
    sender = rdp_sender()
    receiver = rdp_receiver()
    sender.open()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, _ = udp_sock.recvfrom(8192)
            command, seq_num, ack_num, window, payload = parse_packet(message)
            if command == "ACK":
                sender.receive_ack(message)
            else:
                receiver.receive_data(message)

        if udp_sock in writable:
            # If snd_buff is not all 0s, send it then empty it
            if any(snd_buff):
                send_packet(snd_buff)
                snd_buff[:] = [0] * len(snd_buff)

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()
