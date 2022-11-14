'''
Reliable Datagram Protocol (RDP)

A reliable layer on top of UDP. It provides the data transfer between two hosts, the sender and the receiver.
Given an input file, the sender will read the file and send it to the receiver. The receiver will write the data to an output file.
'''

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

# Read file into string
FILE_DATA = ""
with open(read_file_name, "r") as f:
    FILE_DATA += f.read()

# Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind((ip_address, port_number))
udp_sock.connect(("h2", 8888))

# Initialize a queue for the sending buffer
snd_buff = bytearray(2048)

def create_packet(command, seq_num=-1, ack_num=-1, payload=None, window=-1):
    '''
    Create a packet with the given information.

    Parameters:
        command (str): The command of the packet.
        seq_num (int): The sequence number of the packet.
        ack_num (int): The acknowledgement number of the packet.
        payload (str): The payload of the packet.
        window (int): The window size of the packet.

    Returns:
        packet (string): The packet in string format:

        CMD
        Header: value
        Header: value

        PAYLOAD
    '''

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
    '''
    Send a packet to the echo server. Additionally logs the information of the packet.

    Parameters:
        packet (string): The packet to send.
        sender (bool): Whether the packet is sent by the sender or receiver.

    Returns:
        bytes_sent (int): The number of bytes sent.
    '''

    command, seq_num, ack_num, window, payload = parse_packet(packet)
    send_log(command, sender, seq_num, len(payload if payload else ""), ack_num, window)
    bytes_sent = udp_sock.send(packet)
    return bytes_sent

def receive_log(command, sender=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    '''
    Log the information of the received packet.

    Parameters:
        command (str): The command of the packet.
        sender (bool): Whether the packet is sent by the sender or receiver.
        seq_num (int): The sequence number of the packet.
        length (int): The length of the payload of the packet.
        ack_num (int): The acknowledgement number of the packet.
        window (int): The window size of the packet.
    '''

    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if sender:
        print(f"{time}: Receive; {command}; Acknowledgement: {ack_num}; Window: {window}")
    else:
        print(f"{time}: Receive; {command}; Sequence: {seq_num}; Length: {length}")

def send_log(command, sender=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    '''
    Log the information of the sent packet.

    Parameters:
        command (str): The command of the packet.
        sender (bool): Whether the packet is sent by the sender or receiver.
        seq_num (int): The sequence number of the packet.
        length (int): The length of the payload of the packet.
        ack_num (int): The acknowledgement number of the packet.
        window (int): The window size of the packet.
    '''

    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    if sender:
        print(f"{time}: Send; {command}; Sequence: {seq_num}; Length: {length}")
    else:
        print(f"{time}: Send; {command}; Acknowledgement: {ack_num}; Window: {window}")

def write_to_byte_array(byte_array, data, offset=0):
    '''
    Write the data to the byte array at the given offset.

    Parameters:
        byte_array (bytearray): The byte array to write to.
        data (str): The data to write.
        offset (int): The offset to write to.
    '''

    for i in range(len(data)):
        curr = data[i] if type(data[i]) is int else ord(data[i])
        byte_array[offset + i] = curr

def parse_packet(packet):
    '''
    Parse the packet and return the information of the packet.

    Parameters:
        packet (string): The packet to parse.

    Returns:
        command (str): The command of the packet.
        seq_num (int): The sequence number of the packet.
        ack_num (int): The acknowledgement number of the packet.
        window (int): The window size of the packet.
        payload (str): The payload of the packet.
    '''

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
    '''
    The state of the sender.
    '''
    CLOSED = 0
    SYN_SENT = 1
    OPEN = 2
    FIN_SENT = 3

class rdp_sender:
    '''
    The sender of the reliable data transfer protocol.
    '''

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
            if self._ack >= len(FILE_DATA):
                self.close()

            max_send = min(self._window, 1024)
            # Get the next max_send bytes of data
            payload = FILE_DATA[(self._ack - 1):self._ack + max_send - 1]
            packet = create_packet("DAT", self._ack, payload=payload)
            write_to_byte_array(snd_buff, packet)
        if self._state == State.FIN_SENT:
            packet = create_packet("FIN", self._ack)
            write_to_byte_array(snd_buff, packet)

    def open(self):
        '''
        Open the connection.
        '''

        self._state = State.SYN_SENT
        self._send()

    def receive_ack(self, ack):
        '''
        Receive an acknowledgement.
        '''

        # Parse ack
        command, _, ack_num, window, __ = parse_packet(ack)
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
        '''
        Close the connection.
        '''

        self._state = State.FIN_SENT
        self._send()

    def get_state(self):
        '''
        Get the state of the sender.
        '''

        return self._state

class rdp_receiver:
    '''
    The receiver of the reliable data transfer protocol.
    '''

    def __init__(self):
        self._window = 2048
        self._rcv_buff = ""

    def receive_data(self, data):
        '''
        Receive data from the sender.
        '''

        command, seq_num, ack_num, window, payload = parse_packet(data)
        receive_log(command, False, seq_num=seq_num, length=len(payload))
        # Decrease the window
        self._window -= len(payload)
        # If the window is 0, empty the buffer to file
        if self._window == 0 and len(payload) > 0 or command == "FIN":
            # Write to file
            with open(write_file_name, "a") as f:
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
    '''
    The main function.
    '''

    sender = rdp_sender()
    receiver = rdp_receiver()
    sender.open()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, _ = udp_sock.recv(8192)
            command, _, __, ___, ____ = parse_packet(message)
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
