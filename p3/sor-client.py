"""
python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*
If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection
"""

import sys
import socket
import select
from rdp import RDP, State
from datetime import datetime
import re

buff = []

response_pattern = r"HTTP\/1.0(.*)(\r\n|\n)Connection:(.*)(\r\n|\n)Content-Length:\s(\d+)(\r\n|\n)(\r\n|\n)(.*)"

def process_response(response):
    '''
    Processes a HTTP response and returns the payload
    '''
    # Get rid of empty line at start of response if it is there
    response = response[2:] if response[:2] == "\r\n" else response
    response = response[1:] if response[0] == "\n" else response
    # print("=========================================")
    # print(response)
    # print("=========================================")
    if re.match(response_pattern, response, re.S):
        match = re.match(response_pattern, response, re.S)
        length = int(match.group(5))
        payload = match.group(8)
        return payload, length
    else:
        # print("Not matched")
        return response, 0

def log(commands, send=True, seq_num=-1, length=-1, ack_num=-1, window=-1):
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

    rdp = RDP(client_buffer_size, client_payload_length, test=True)

    request = "GET /" + read_file_name + " HTTP/1.0\r\n"
    request += "Connection: keep-alive\r\n"

    rdp.add_data(request)
    rdp.send_packet()

    wrote = False
    data = ""
    p_length = 0

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if rdp._state == State.CLOSED and rdp._fin_sent:
            with open(write_file_name, "w") as f:
                f.write(data)
            sys.exit(0)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(client_buffer_size)
            commands, seq_num, length, ack_num, window, payload = rdp.parse_packet(message)
            log(commands, False, seq_num, length, ack_num, window)
            # Close the connection if 400 or 404
            if "400" in payload or "404" in payload:
                sys.exit(1)
            if("RST" in commands):
                sys.exit(1)
            response = rdp.receive_packet(message)
            if response:
                payload, length = process_response(payload)
                # rdp.set_content_length(length)
                # Set p_length to max of p_length and length
                p_length = max(p_length, length)
                # p_length = length
                data += payload

        if udp_sock in writable:
            # Check for any timeouts
            rdp.timeout()
            packet = rdp.pop_queue()
            if packet:
                commands, seq_num, length, ack_num, window, payload = rdp.parse_packet(packet)
                log(commands, True, seq_num, length, ack_num, window)
                udp_sock.sendto(packet, (server_ip_address, server_udp_port_number))

        if udp_sock in exceptional:
            print("exceptional")

if __name__ == "__main__":
    main()