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

# # Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Initialize the sending buffer as an array
snd_buff = bytearray(1024)

# Initialize the receiving buffer
rcv_buff = bytearray(1024)

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

def log(command, send=True):
    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    send_msg = "Send" if send else "Receive"
    final_msg = "Length" if send else "Window"
    print(f"{time}: {send_msg}; {command}; Sequence: number; {final_msg}: number")

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    OPEN = 2
    FIN_SENT = 3

class rdp_sender:
    def __init__(self, ip, port):
        self._state = State.CLOSED

    def _send(self):
        if self._state == State.SYN_SENT:
            # Write SYN rdp packet into snd_buff
            pass
        elif self._state == State.OPEN:
            # Write the available window of DAT rdp packets into snd_buff
            # if all data has been sent, call self.close()
            pass
        elif self._state == State.FIN_SENT:
            # Write FIN rdp packet into snd_buff
            pass

    def open(self):
        # Write SYN rdp packet into snd_buff
        packet = create_packet("SYN")
        write_to_byte_array(snd_buff, packet)

        self._state = State.SYN_SENT

    def receive_data(self, data):
        # Write data into the receiving buffer
        pass

    def receive_ack(self, ack):
        if self._state == State.SYN_SENT:
            # if acknowledgement number is correct, change state to OPEN
            pass
        elif self._state == State.OPEN:
            # if three duplicate ACKs are received, resend packets
            # if acknowledgement number is correct, move the sliding window, call self.send()
            pass
        elif self._state == State.FIN_SENT:
            # if acknowledgement number is correct, change state to CLOSED
            pass

    def timeout(self):
        if self._state != State.CLOSED:
            # Rewrite the rdp packets in snd_buff
            pass
        pass

    def close(self):
        # Write FIN rdp packet into snd_buff
        self._state = State.FIN_SENT

    def get_state(self):
        return self._state

class rdp_receiver:
    def __init__(self, ip, port):
        self._state = State.CLOSED

    def send(self, data):
        pass

    def receive(self):
        pass

    def open(self):
        pass

    def get_state(self):
        return self._state

def main():
    # Create a rdp_sender object
    sender = rdp_sender(ip_address, port_number)
    receiver = rdp_receiver(ip_address, 8888)
    sender.open()

    # # Read data from the file
    # with open(read_file_name, 'rb') as f:
    #     data = f.read()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        print("readable: ", readable)
        # print("writable: ", writable)
        # print("exceptional: ", exceptional)

        if udp_sock in readable:
            message, address = udp_sock.recvfrom(8192)
            print("message: ", message)
            write_to_byte_array(rcv_buff, message)

            # if message cannot be recognized
            if not is_recognizable(rcv_buff):
                # write RST packet into snd_buff
                pass

            # if message in rcv_buf is complete
            if is_complete(rcv_buff):
                # if message is ACK
                if rcv_buff[0] == 0:
                    sender.receive_ack(message)
                else:
                    sender.receive_data(message)

        if udp_sock in writable:
            bytes_sent = udp_sock.sendto(snd_buff, (ip_address, 8888))
            log("SYN", True)
            print(f"Sent {bytes_sent} bytes")

        if udp_sock in exceptional:
            sender.close()
            receiver.close()
            break

        if not(readable or writable or exceptional):
            if receiver.get_state() == State.CLOSED and sender.get_state() == State.CLOSED:
                break
            sender.timeout()

if __name__ == '__main__':
    main()
