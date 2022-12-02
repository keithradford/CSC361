from enum import Enum
import sys

class State(Enum):
    CLOSED = 0
    SYN_SENT = 1
    SYN_RCVD = 2
    CONNECTED = 3
    FIN_SENT = 4
    FIN_RCVD = 5
    CON_FIN_RCVD = 6

class RDP:
    '''
    The sender of the reliable data transfer protocol
    '''

    def __init__(self, window, payload_length):
        self._state = State.CLOSED
        self._seq = 0
        self._window = window
        self._data = ""
        self._payload_length = payload_length
        self._ack = 0
        self._receiver_window = window

        # Initialize buff as a queue of byte arrays
        self._buff = [b""] * window
        self._acked = [False] * window
        self._timer = [None] * window

    def get_buff(self):
        return self._buff

    def set_buff(self, buff):
        self._buff = buff

    def add_data(self, data):
        self._data += data

    def is_closed(self):
        return self._state == State.CLOSED

    def timeout(self):
        pass

    def create_packet(self, commands, seq_num=-1, ack_num=-1, window=-1, payload=""):
        '''
        Create a packet from the given components.
        '''
        payload_length = len(payload) if payload else 0
        packet = "|".join(commands) + "\n"
        packet += "Sequence: " + str(seq_num) + "\n"
        packet += "Length: " + str(payload_length) + "\n"
        packet += "Acknowledgement: " + str(ack_num) + "\n"
        packet += "Window: " + str(window) + "\n"
        packet += "\n" + payload if payload else ""

        return packet.encode()

    def parse_packet(self, packet):
        '''
        Parse a packet into its components.
        '''

        lines = packet.decode().splitlines()
        commands = lines[0].split("|")
        # Sequence: #
        seq_num = int(lines[1].split(": ")[1])
        # Length: #
        length = int(lines[2].split(": ")[1])
        # Acknowledgement: #
        ack_num = int(lines[3].split(": ")[1])
        # Window: #
        window = int(lines[4].split(": ")[1])
        # Payload = remaining lines
        payload = "\n".join(lines[5:])

        return commands, seq_num, length, ack_num, window, payload

    def send_packet(self):
        commands = []
        packets = []
        if self._state == State.CLOSED:
            print("Going from CLOSED to SYN_SENT")
            commands.append("SYN")
            self._state = State.SYN_SENT
        if self._state == State.SYN_RCVD:
            print("Going from SYN_RCVD to SYN_SENT")
            commands.append("SYN")
            self._state = State.SYN_SENT
        if self._state == State.FIN_RCVD:
            print("Going from FIN_RCVD to FIN_SENT")
            commands.append("FIN")
            self._state = State.FIN_SENT
        if self._state == State.CONNECTED:
            print("Going from CONNECTED to FIN_SENT")
            commands.append("FIN")
            self._state = State.FIN_SENT
        if self._state == State.CON_FIN_RCVD:
            print("Going from CON_FIN_RCVD to FIN_SENT")
            commands.append("FIN")
            self._state = State.FIN_SENT

        # Create DAT packets if there is data to send
        if self._data[self._seq:self._seq + self._payload_length]:
            commands.append("DAT")
            while self._payload_length < self._receiver_window:
                packet = self.create_packet(commands + ["ACK"] + ["FIN"] if len(self._data[self._seq:self._seq + self._payload_length]) < self._receiver_window else [], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[self._seq:self._seq + self._payload_length])
                packets.append(packet)
                self._buff[self._seq % self._window] = packet
                # If it's the last packet, break
                if len(self._data[self._seq:self._seq + self._payload_length]) < self._receiver_window:
                    self._state = State.FIN_SENT
                    self._receiver_window -= len(self._data[self._seq:self._seq + self._payload_length])
                    break
                self._receiver_window -= self._payload_length
                self._seq += self._payload_length
                commands = ["DAT"]
        else:
            packet = self.create_packet(commands + ["ACK"], self._seq, self._ack, window=self._window)
            # print(f"Sending packet: {packet}")
            packets.append(packet)
            self._buff[self._seq % self._window] = packet

        return packets if len(commands) > 0 else []

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)

        if length > self._window:
            self.send_packet(["RST"], seq_num=0, ack_num=-1, window=self._window)
            return
        # print(commands)
        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1
        self._receiver_window = window

        # TODO: Handle DAT, detect correct ACK, send FINs

        send_commands = []
        if self._state == State.CLOSED:
            if "SYN" in commands:
                print("Going from CLOSED to SYN_RCVD")
                # send_commands.append("SYN")
                self._state = State.SYN_RCVD
            # if "DAT" in commands:
            #     send_commands.append("DAT")
                # self._data = self.process_request(payload.strip())
        if self._state == State.SYN_RCVD:
            # if "FIN" in commands:
            print("Going from SYN_RCVD to FIN_RCVD")
            self._state = State.FIN_RCVD
        if self._state == State.SYN_SENT:
            if "ACK" in commands:
                print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
            # if "DAT" in commands:
            #     send_commands.append("DAT")
                # self._data = self.process_request(payload.strip())
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
                # send_commands.append("FIN")
            # if "DAT" in commands:
            #     send_commands.append("DAT")
                # self._data = self.process_request(payload.strip())

        # if self._state == State.FIN_SENT:
        #     if "ACK" in commands and "FIN" in commands:
        #         self.send_packet(["ACK"], self._seq, self._ack)
        #     else:
        #         # print("Going from FIN_SENT to CLOSED")
        #         self._state = State.CLOSED

        # if "DAT" in send_commands:
        #     while self._payload_length < window:
        #         self.send_packet(send_commands + ["ACK"] + ["FIN"] if len(self._data) < self._window else [], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[:self._payload_length])
        #         # If it's the last packet, break
        #         if len(self._data) < window:
        #             self._state = State.FIN_SENT
        #             window -= len(self._data)
        #             break
        #         window -= self._payload_length
        #         self._data = self._data[self._payload_length:]
        # else:
        #     self.send_packet(send_commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window)

        return payload if "DAT" in commands else None
