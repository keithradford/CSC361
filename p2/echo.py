import socket
import sys

def show_usage():
    print("Usage: ./echo.py <host> <port>", file=sys.stderr)

def main():
    if len(sys.argv) != 3 or not sys.argv[2].isascii() or not sys.argv[2].isdigit():
        show_usage()
        raise SystemExit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind((host, port))

    while True:
        msg, address = sock.recvfrom(8192)
        sock.sendto(msg, address)


if __name__ == "__main__":
    main()