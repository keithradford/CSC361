"""
python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*
If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection
"""

import sys
import socket
import select
from rdp import RDP
from datetime import datetime

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

def log(self, commands, send=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
    '''
    Log the information of the received packet.

    Parameters:
        commands (str[]): The commands of the packet.
        sender (bool): Whether the packet is being sent or received.
        seq_num (int): The sequence number of the packet.
        length (int): The length of the payload of the packet.
        ack_num (int): The acknowledgement number of the packet.
        window (int): The window size of the packet.
    '''

    # Format the current time
    time = datetime.now().strftime("%a %b %d %H:%M:%S PDT %Y")
    send_receive = "Send" if send else "Receive"
    joined_commands = "|".join(commands)
    print(f"{time}: {send_receive}; {joined_commands}; Sequence: {seq_num}; Length: {length}; Acknowledgement: {ack_num}; Window: {window}")

def main():
    # Check for correct number of arguments
    if len(sys.argv) < 7 or len(sys.argv) % 2 != 1:
        print("Usage: python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*")
        print("* If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection")
        sys.exit(1)

    server_ip_address = sys.argv[1]
    server_udp_port_number = int(sys.argv[2])
    client_buffer_size = int(sys.argv[3])
    client_payload_length = int(sys.argv[4])
    read_file_name = sys.argv[5]
    write_file_name = sys.argv[6]

    # Initialize UDP socket and bind to server IP address and port number
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    rdp = RDP(client_buffer_size)
    fin_sent = False

    request = "GET /" + read_file_name + " HTTP/1.0\r\n"
    request += "Connection: keep-alive\r\n"

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(client_buffer_size)
            # print("Client received message from " + str(client_address) + ": " + message.decode())
            rdp.receive_packet(message)
            if fin_sent and "ACK" in message.decode().splitlines()[0]:
                sys.exit(0)

        if udp_sock in writable:
            if buff:
                packet = buff.pop(0)
                # print("Client sending message to " + str((server_ip_address, server_udp_port_number)) + ": " + packet.decode())
                udp_sock.sendto(packet, (server_ip_address, server_udp_port_number))
                if "FIN" in packet.decode():
                    fin_sent = True

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()