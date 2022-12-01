class RDP:
    '''
    The sender of the reliable data transfer protocol
    '''

    def __init__(self, window):
        self._state = State.CLOSED
        self._seq = 0
        self._window = window
        self._data = ""
        self._ack = 0

        # Create initial HTTP request
        self.send_packet(["SYN", "ACK", "DAT"], 0, -1, self._window, request)

    def get_state(self):
        return self._state

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

    def send_packet(self, commands, seq_num=-1, ack_num=-1, window=-1, payload=""):
        if self._state == State.CLOSED and ack_num != -1:
            return
        if self._state == State.CLOSED:
            if "SYN" in commands:
                # print("Going from CLOSED to SYN_SENT")
                self._state = State.SYN_SENT
        if self._state == State.SYN_RCVD:
            if "SYN" in commands:
                # print("Going from SYN_RCVD to CONNECTED")
                self._state = State.SYN_SENT
        if self._state == State.FIN_RCVD:
            if "FIN" in commands:
                # print("Going from FIN_RCVD to CLOSED")
                self._state = State.FIN_SENT
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to FIN_SENT")
                self._state = State.FIN_SENT
        if self._state == State.CON_FIN_RCVD:
            if "FIN" in commands:
                # print("Going from CON_FIN_RCVD to FIN_SENT")
                self._state = State.FIN_SENT

        packet = self.create_packet(commands, seq_num, ack_num, window, payload)

        self.log(commands, True, seq_num, len(payload), ack_num, window)
        buff.append(packet)

    def receive_packet(self, data):
        commands, seq_num, length, ack_num, window, payload = self.parse_packet(data)
        self.log(commands, False, seq_num, length, ack_num, window)

        self._seq = ack_num if ack_num != -1 else self._seq
        self._ack = seq_num + length + 1

        # TODO: Handle DAT, detect correct ACK, send FINs
        if "DAT" in commands:
            self._data += process_response(payload.strip())
        send_commands = []
        if self._state == State.CLOSED:
            if "SYN" in commands:
                # print("Going from CLOSED to SYN_RCVD")
                send_commands.append("SYN")
                self._state = State.SYN_RCVD
        if self._state == State.SYN_RCVD:
            if "FIN" in commands:
                # print("Going from SYN_RCVD to FIN_RCVD")
                self._state = State.FIN_RCVD
        if self._state == State.SYN_SENT:
            if "ACK" in commands:
                # print("Going from SYN_SENT to CONNECTED")
                self._state = State.CONNECTED
        if self._state == State.CONNECTED:
            if "FIN" in commands:
                # print("Going from CONNECTED to CON_FIN_RCVD")
                self._state = State.CON_FIN_RCVD
                send_commands.append("FIN")

        # Send packet for first chunk of data
        self.send_packet(send_commands + ["ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[:self._window])
        # Send packets for remaining data
        for i in range(self._window, len(self._data), self._window):
            self.send_packet(["DAT", "ACK"], seq_num=self._seq, ack_num=self._ack, window=self._window, payload=self._data[i:i+self._window])

        if self._state == State.FIN_SENT:
                # print("Going from FIN_SENT to CLOSED")
                self._state = State.CLOSED
                # Write data to file
                with open(write_file_name, "w") as f:
                    f.write(self._data)
                # TODO: Replace this with timeout