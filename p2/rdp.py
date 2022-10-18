# Reliable Datagram Protocol
import socket
import select
import sys
from enum import Enum

ip_address = sys.argv[1]
port_number = int(sys.argv[2])
read_file_name = sys.argv[3]
write_file_name = sys.argv[4]

# Initialize a UDP socket
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Initialize the sending buffer
snd_buff = []

# Initialize the receiving buffer
rcv_buff = []


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
        pass

    def send(self, data):
        pass

    def receive(self):
        pass

    def open(self):
        pass

def main():
    rdp_sender.open()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        print("readable: ", readable)
        print("writable: ", writable)
        print("exceptional: ", exceptional)

        if not(readable or writable or exceptional):
            # Timeout
            pass

        if udp_sock in readable:
            # Receive data and append to rcv_buff
            pass

        if udp_sock in writable:
            bytes_sent = rdp_sender.send(snd_buff)

        if udp_sock in exceptional:
            rdp_sender.close()
            rdp_receiver.close()
            break

if __name__ == '__main__':
    main()
