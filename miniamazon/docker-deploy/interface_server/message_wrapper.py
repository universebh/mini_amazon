import world_amazon_pb2 as wapb
import config as cfg
import socket as skt
from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint
from socket import error as SocketError
from google.protobuf.message import DecodeError

class MessageWrapper:
    def __init__(self, message):
        self._message = message
        self._cmd_data = None

    def get_message(self):
        return self._message

    def get_data(self):
        return self._cmd_data

    def parse_itself(self, cmd_type):
        res = cmd_type()
        res.ParseFromString(self._message)
        return res

    def encode_and_send(self, socket):
        _EncodeVarint(socket.send, len(self._message), None)
        socket.send(self._message)
    
    def recv_and_parse(self, socket, cmd_type):
        self._message = b''
        var_int_buff = []
        try:
            while True:
                buf = socket.recv(1)
                var_int_buff += buf
                msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
                if new_pos != 0:
                    break
        except skt.timeout as e:
            raise skt.timeout()
        except SocketError as e:
            raise SocketError('receive byte length: {}.'.format(e))
        try:
            self._message = socket.recv(msg_len)
        except SocketError as e:
            raise SocketError('receive message: {}.'.format(e))

        self._cmd_data = cmd_type()
        # try:
        self._cmd_data.ParseFromString(self._message)
        # except DecodeError as e:
        #     cfg.logger.debug('Error when parsing: {}'.format(self._message.decode('utf-8')))