# python3 sor-server.py server_ip_address server_udp_port_number server_buffer_size server_payload_length
import sys

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

if __name__ == "__main__":
    main()