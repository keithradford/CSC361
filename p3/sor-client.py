"""
python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*
If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection
"""

import sys
import socket
import select
from enum import Enum

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    SYN_RCVD = 2
    CONNECTED = 3
    FIN_SENT = 4
    FIN_RCVD_1 = 5
    FIN_RCVD_2 = 6

class rdp_sender:
    '''
    The sender of the reliable data transfer protocol
    '''

    def __init__(self):
        self._state = State.CLOSED
        self._ack = 0
        self._window = 0

    def _send(self):
        if self._state == State.SYN_RCVD:
            pass
        if self._state == State.SYN_SENT:
            # packet = create_packet("SYN", 0)
            # write_to_byte_array(snd_buff, packet)
            pass
        if self._state == State.CONNECTED:
            # If all the data has been sent, close
            # if self._ack >= len(FILE_DATA):
                # self.close()

            max_send = min(self._window, 1024)
            # Get the next max_send bytes of data
            # payload = FILE_DATA[(self._ack - 1):self._ack + max_send - 1]
            # packet = create_packet("DAT", self._ack, payload=payload)
            # write_to_byte_array(snd_buff, packet)
        if self._state == State.FIN_SENT:
            # packet = create_packet("FIN", self._ack)
            # write_to_byte_array(snd_buff, packet)
            pass
        if self._state == State.FIN_RCVD_1:
            pass
        if self._state == State.FIN_RCVD_2:
            pass

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
        # command, _, ack_num, window, __ = parse_packet(ack)
        # receive_log(command, True, ack_num=ack_num, window=window)
        # self._ack = ack_num
        # self._window = window
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

        # command, seq_num, ack_num, window, payload = parse_packet(data)
        # receive_log(command, False, seq_num=seq_num, length=len(payload))
        # Decrease the window
        # self._window -= len(payload)
        # If the window is 0, empty the buffer to file
        # if self._window == 0 and len(payload) > 0 or command == "FIN":
            # Write to file
            # with open(write_file_name, "a") as f:
            #     f.write(self._rcv_buff)
            # Reset the buffer and window
            # self._rcv_buff = ""
            # self._window = 2048
        # if len(payload) > 0:
            # Add to buffer
        #     self._rcv_buff += payload
        # padding = len(payload) - 1 if len(payload) > 0 else 0
        # packet = create_packet("ACK", ack_num=seq_num + padding + 1, window=self._window)
        # send_packet(packet.encode(), False)
        pass

def main():
    # Check for correct number of arguments
    if len(sys.argv) < 7 or len(sys.argv) % 2 != 1:
        print("Usage: python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*")
        print("* If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection")
        sys.exit(1)

    # Parse arguments
    server_ip_address = sys.argv[1]
    server_udp_port_number = int(sys.argv[2])
    client_buffer_size = int(sys.argv[3])
    client_payload_length = int(sys.argv[4])
    read_file_name = sys.argv[5]
    write_file_name = sys.argv[6]

    print("Server IP address: " + server_ip_address)
    print("Server UDP port number: " + str(server_udp_port_number))
    print("Client buffer size: " + str(client_buffer_size))
    print("Client payload length: " + str(client_payload_length))
    print("Read file name: " + read_file_name)
    print("Write file name: " + write_file_name)

    # Initialize UDP socket and bind to server IP address and port number
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Create two dictionaries: sending buffer and receiving buffer
    # Key: client address
    # Value: queue or string
    snd_buff = {}
    rcv_buff = {}

    sender = rdp_sender()
    receiver = rdp_receiver()

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(1024)
            print("Client received message from " + str(client_address) + ": " + message.decode())

        if udp_sock in writable:
            msg = "Hello from client"
            udp_sock.sendto(msg.encode(), (server_ip_address, server_udp_port_number))

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()