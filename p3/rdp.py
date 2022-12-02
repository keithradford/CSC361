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

    def __init__(self, window, payload_length, test=False):
        self._state = State.CLOSED
        self._seq = 0
        self._window = window
        self._data = ""
        self._payload_length = payload_length
        self._ack = -1
        self._receiver_window = window

        self._test = test

        # self._send_ack = False
        self._send_rst = False

        # Initialize buff as a queue of byte arrays
        self._buff = [b""] * window
        self._queue = []
        self._timer = [None] * window

        self._closing = False

    def get_buff(self):
        return self._buff

    def pop_queue(self):
        return self._queue.pop(0) if len(self._queue) > 0 else None

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

    def data_man(self, commands):
        payload = None
        if self._data != "":
            payload = self._data[:self._payload_length]
            self._data = self._data[self._payload_length:]
            self._receiver_window -= self._payload_length
            commands.append("DAT")
            if self._data == "":
                if not self._test:
                    commands.append("FIN")
                    # print(f"Going from {self._state} to FIN_SENT")
                    self._state = State.FIN_SENT

        return payload, commands

    def send_packet(self):
        commands = []

        if self._state == State.CLOSED:
            # State evolves to SYN-Sent if send a SYN
            # Sends a SYN if seq is 0
            if self._seq == 0:
                commands.append("SYN")
                # print("Going from CLOSED to SYN_SENT")
                self._state = State.SYN_SENT
                payload, commands = self.data_man(commands)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
                if self._buff[self._seq % self._window] == b"":
                    self._queue.append(packet)
                    self._buff[self._seq % self._window] = packet
        elif self._state == State.SYN_RCVD:
            # State evolves to SYN-Sent if you send a packet with SYN in the command line,
            if self._seq == 0:
                commands.append("SYN")
                # print("Going from SYN_RCVD to SYN_SENT")
                self._state = State.SYN_SENT
                payload, commands = self.data_man(commands)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
                if self._buff[self._seq % self._window] == b"":
                    self._queue.append(packet)
                    self._buff[self._seq % self._window] = packet
        elif self._state == State.CONNECTED:
            # Can send DAT, ACK, or FIN
            payload, commands = self.data_man(commands)
            packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.FIN_SENT:
            payload, commands = self.data_man(commands)
            packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.CON_FIN_RCVD:
            # Can send packets with DAT, FIN, or ACK
            # Evolves to FIN_SENT if sending FIN
            payload = None
            if(self._test):
                # send a FIN
                packet = self.create_packet(["FIN", "ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
                # print("Going from CON_FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT
            else:
                payload, commands = self.data_man(commands)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.FIN_RCVD:
            # Can send FIN or ACK
            # Evolves to FIN_SENT if sending FIN
            payload, commands = self.data_man(commands)
            packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._buff[self._seq % self._window] = packet

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)

        if length > self._window:
            self._queue = [self.create_packet(["RST"], seq_num=self._seq, ack_num=-1, window=self._receiver_window)]
            return None

        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1
        self._receiver_window = window

        self._buff[self._seq % self._window] = b""

        if self._state == State.CLOSED:
            if "SYN" in commands:
                self._closing = False
                # print("Going from CLOSED to SYN_RCVD")
                self._state = State.SYN_RCVD
        elif self._state == State.SYN_RCVD:
            if "FIN" in commands:
                # print("Going from SYN_RCVD to FIN_RCVD")
                self._state = State.FIN_RCVD
        elif self._state == State.SYN_SENT:
            if "ACK" in commands:
                # print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
                if self._test:
                    self.send_packet()
        elif self._state == State.FIN_SENT:
            if "ACK" in commands and "FIN" in commands:
                packet = self.create_packet(["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window)
                self._queue.append(packet)
                self._state = State.CLOSED
                return payload
            else:
                # print("Going from FIN_SENT to CLOSED")
                self._state = State.CLOSED
                self._queue = []
                self._buff = [b""] * self._window

        return payload
