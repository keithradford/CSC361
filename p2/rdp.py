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
data = []

# # Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Initialize the sending buffer as an array
snd_buff = bytearray(1024)

# Initialize the receiving buffer
rcv_buff = bytearray(1024)

# Read data from file
with open(read_file_name, 'rb') as f:
    data += f.read()

def create_packet(command, seq_num=-1, ack_num=-1, payload=None):
    packet = f"{command}\r\n"
    if seq_num != -1:
        packet += f"Sequence: {seq_num}\r\n"
    if ack_num != -1:
        packet += f"Acknowledgment: {ack_num}\r\n"
    if payload is not None:
        packet += f"Length: {len(payload)}\r\n\r\n"
        packet += f"{payload}\r\n"

    return packet

# Helper method to check if a message is complete
def is_complete(message):
    return True

# Helper method to check if a message can be recognized
def is_recognizable(message):
    return True

# Helper function to write to a byte array
def write_to_byte_array(byte_array, data, offset=0):
    for i in range(len(data)):
        curr = data[i] if type(data[i]) is int else ord(data[i])
        byte_array[offset + i] = curr

def log(command, send=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if send:
        print(f"{time}: Send; {command}; Sequence: {seq_num}; Length: {length}")
    else:
        print(f"{time}: Receive; {command}; Acknowledgement: {ack_num}; Window: {window}")

def send_packet(packet):
    bytes_sent = udp_sock.sendto(packet, (ip_address, 8888))
    return bytes_sent

def is_ack(message):
    msg = message.decode("utf-8")
    return msg.startswith("ACK")

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

def space_remaining(byte_arrary):
    return byte_arrary.count(0)

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
            # Write SYN rdp packet into snd_buff
            packet = create_packet("SYN")
            print("Sender Sent SYN")
            write_to_byte_array(snd_buff, packet)

        elif self._state == State.OPEN:
            # if all data has been sent, call self.close()
            if len(data) == 0:
                self.close()
                return

            # Write DAT rdp packet into snd_buff
            packet = create_packet("DAT", payload=data[:1024], seq_num=0)
            print("Sender Sent DAT")
            write_to_byte_array(snd_buff, packet, offset=100)
            print("Asfgijsd", snd_buff)
            # Remove from data
            data[:1024] = []
        elif self._state == State.FIN_SENT:
            # Write FIN rdp packet into snd_buff
            packet = create_packet("FIN")
            write_to_byte_array(snd_buff, packet)

    def open(self):
        self._state = State.SYN_SENT
        self._send()

    def receive_ack(self, ack):
        # log("ACK", send=False)
        command, __, ack_num, ___ = parse_packet(ack)
        print("Sender Receive", command, self._state)
        if self._state == State.SYN_SENT:
            # if acknowledgement number is correct, change state to OPEN
            _, __, ack_num, ___ = parse_packet(ack)
            if ack_num == 0:
                self._state = State.OPEN
        elif self._state == State.OPEN:
            # if three duplicate ACKs are received, resend packets
            # if acknowledgement number is correct, move the sliding window, call self.send()
            self._send()
        elif self._state == State.FIN_SENT:
            # if acknowledgement number is correct, change state to CLOSED
            self._state = State.CLOSED

    def timeout(self):
        if self._state != State.CLOSED:
            # Rewrite the rdp packets in snd_buff
            pass
        pass

    def close(self):
        # Write FIN rdp packet into snd_buff
        self._state = State.FIN_SENT
        self._send()

    def get_state(self):
        return self._state

class rdp_receiver:
    def __init__(self):
        self._state = State.CLOSED

    def send(self, data):
        pass

    def receive(self):
        pass

    def open(self):
        pass

    def receive_data(self, data):
        # Parse packet
        command, seq_num, ack_num, payload = parse_packet(data)
        print("Receiver Receive", command)
        # log(command, send=False)
        self._state = State.OPEN
        packet = create_packet("ACK", ack_num=0)
        print("Receiver Sent ACK")
        send_packet(packet.encode())
        # log("ACK", send=True)

    def get_state(self):
        return self._state

def main():
    # Create a rdp_sender object
    sender = rdp_sender()
    receiver = rdp_receiver()
    sender.open()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        # print("readable: ", readable)
        # print("writable: ", writable)
        # print("exceptional: ", exceptional)

        if udp_sock in readable:
            message, address = udp_sock.recvfrom(8192)
            write_to_byte_array(rcv_buff, message)
            # print(rcv_buff)

            # if message cannot be recognized
            if not is_recognizable(message):
                # write RST packet into snd_buff
                pass

            # if message in rcv_buf is complete
            if is_complete(message):
                # if message is ACK
                if is_ack(message):
                    sender.receive_ack(message)
                else:
                    receiver.receive_data(message)

        if udp_sock in writable:
            bytes_sent = send_packet(snd_buff)
            # log("SYN", True)
            # print(f"Sent {bytes_sent} bytes")

        if udp_sock in exceptional:
            sender.close()
            receiver.close()
            break

        if sender.get_state() == State.CLOSED:
            break

        if not(readable or writable or exceptional):
            if receiver.get_state() == State.CLOSED and sender.get_state() == State.CLOSED:
                break
            sender.timeout()

if __name__ == '__main__':
    main()
