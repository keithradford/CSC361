# python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length
import sys
import select
import socket

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

    clients = {}

    while True:
        readable, writable, exceptional = select.select([udp_sock], [udp_sock], [udp_sock], 0.1)

        if udp_sock in readable:
            message, client_address = udp_sock.recvfrom(server_buffer_size)
            clients[client_address] = message
            print("Server received message from " + str(client_address) + ": " + message.decode())

        if udp_sock in writable:
            for c in clients:
                msg = f"Hello from server to {c}"
                udp_sock.sendto(msg.encode(), c)


        if udp_sock in exceptional:
            pass

if __name__ == "__main__":
    main()