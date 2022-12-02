from enum import Enum
from datetime import datetime, timedelta

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
        self._hello = 0
        self._receiver_window = window

        self._duplicate = False

        self._test = test

        # self._send_ack = False
        self._send_rst = False
        self._fin_rcvd = False
        self._fin_sent = False

        # Initialize buff as a queue of byte arrays
        self._buff = [b""] * window
        self._queue = []
        self._timer = [None] * window

        self._closing = False

        self._content_length = 0

    def get_buff(self):
        return self._buff

    def set_content_length(self, length):
        self._content_length = length

    def pop_queue(self):
        return self._queue.pop(0) if len(self._queue) > 0 else None

    def set_buff(self, buff):
        self._buff = buff

    def add_data(self, data):
        self._data += data

    def is_closed(self):
        return self._state == State.CLOSED

    def timeout(self):
        '''
        Send the packet at the front of the queue again.
        '''
        # If now is passed timer value
        if self._timer[self._seq % self._window] == None or self._state == State.CLOSED:
            return
        if datetime.now() > self._timer[self._seq % self._window]:
            print("timeout")
            packet = self._buff[self._seq % self._window]
            self._queue.append(packet)
            self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)

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
            # -------- HERE IS WHERE I LEFT OFF -------- #
            self._content_length -= self._payload_length
            if not "DAT" in commands:
                commands.append("DAT")
            if self._data == "":
                if not self._test:
                    commands.append("FIN")
                    # self._state = State.FIN_SENT
                    self._fin_sent = True

        return payload, commands

    def send_packet(self, sender=0):
        self._hello += 1
        commands = []
        # # # print("sending in state: " + str(self._state))
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
                    self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                    self._buff[self._seq % self._window] = packet
        elif self._state == State.SYN_RCVD:
            # State evolves to SYN-Sent if you send a packet with SYN in the command line,
            if self._seq == 0:
                commands.append("SYN")
                # print("Going from SYN_RCVD to SYN_SENT")
                self._state = State.SYN_SENT
                payload, commands = self.data_man(commands)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
                # # # print(packet)
                if self._buff[self._seq % self._window] == b"":
                    self._queue.append(packet)
                    self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                    self._buff[self._seq % self._window] = packet
        elif self._state == State.CONNECTED:
            # Can send DAT, ACK, or FIN
            if len(self._data) > self._payload_length:
                i = self._payload_length
                j = 0
                while i < self._window and len(self._data) > self._payload_length:
                    payload, commands = self.data_man(commands)
                    # print("looping", self._seq, self._ack + j, commands, self._hello, sender)
                    packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack + j, window=self._window, payload=payload)
                    if self._buff[self._seq % self._window] == b"":
                        self._queue.append(packet)
                        self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                        self._buff[self._seq % self._window] = packet
                    i += self._payload_length
                    j += 1
            else:
                payload, commands = self.data_man(commands)
                # print("did not loop", self._seq, self._ack, commands, self._hello, sender)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack + sender, window=self._window, payload=payload)
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.FIN_SENT:
            payload, commands = self.data_man(commands)
            packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.CON_FIN_RCVD:
            # Can send packets with DAT, FIN, or ACK
            # Evolves to FIN_SENT if sending FIN
            payload = None
            if(self._test):
                # send a FIN
                packet = self.create_packet(["FIN", "ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._buff[self._seq % self._window] = packet
                # print("Going from CON_FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT
                self._fin_sent = True
            else:
                payload, commands = self.data_man(commands)
                packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._buff[self._seq % self._window] = packet
        elif self._state == State.FIN_RCVD:
            # Can send FIN or ACK
            # Evolves to FIN_SENT if sending FIN
            payload, commands = self.data_man(commands)
            packet = self.create_packet(commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=payload)
            if self._buff[self._seq % self._window] == b"":
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._buff[self._seq % self._window] = packet

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)

        if length > self._window:
            self._queue = [self.create_packet(["RST"], seq_num=self._seq, ack_num=-1, window=self._receiver_window)]
            return None

        # Check if the packet is a duplicate
        if self._seq == ack_num:
            print("Duplicate packet", self._seq)
            packet = self._buff[self._seq % self._window]
            # Requeue packet
            self._queue.append(packet)
            self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
            return None

        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1
        self._receiver_window = window

        self._buff[self._seq % self._window] = b""

        if self._fin_sent:
            self._state = State.FIN_SENT
            # # print(f"Going from {self._state} to FIN_SENT")

        if self._state == State.CLOSED:
            if "SYN" in commands:
                self._closing = False
                self._fin_sent = False
                # print("Going from CLOSED to SYN_RCVD")
                self._state = State.SYN_RCVD
            if len(self._data):
                self.send_packet()
        elif self._state == State.SYN_RCVD:
            if "FIN" in commands:
                # print("Going from SYN_RCVD to FIN_RCVD")
                self._state = State.FIN_RCVD
            if len(self._data):
                self.send_packet()
        elif self._state == State.SYN_SENT:
            if "ACK" in commands:
                # print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
                if "FIN" in commands:
                    # print("Going from CONNECTED to CON_FIN_RCVD")
                    self._state = State.CON_FIN_RCVD
                    self.send_packet()
                elif len(self._data) or "DAT" in commands:
                    self.send_packet()
        elif self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
            if len(self._data) or "DAT" in commands:
                self.send_packet()
        elif self._state == State.FIN_SENT:
            if "ACK" in commands and "FIN" in commands:
                packet = self.create_packet(["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window)
                self._queue.append(packet)
                self._timer[self._seq % self._window] = datetime.now() + timedelta(seconds=1)
                self._state = State.CLOSED
                return payload
            else:
                # print("Going from FIN_SENT to CLOSED")
                self._state = State.CLOSED
                self._queue = []
                self._buff = [b""] * self._window

        return payload
