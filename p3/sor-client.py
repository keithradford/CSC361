# python3 sor-client.py server_ip_address server_udp_port_number client_buffer_size client_payload_length read_file_name write_file_name [read_file_name write_file_name]*
# If there are multiple pairs of read_file_name and write_file_name in the command line, it indicates that the SoR client shall request these files from the SoR server in a persistent HTTP session over an RDP connection
import sys

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

if __name__ == "__main__":
    main()