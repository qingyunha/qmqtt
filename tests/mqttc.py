import socket
import selectors
from collections import deque
from uuid import uuid1

# packet types
CONNECT = 1
CONNACK = 2
PUBLISH = 3
PUBACK = 4
PUBREC = 5
PUBREL = 6
PUBCOMP = 7
SUBSCRIBE = 8
SUBACK = 9
UNSUBSCRIBE = 10
UNSUBACK = 11
PINGREQ = 12
PINGRESP = 13
DISCONNECT = 14

PACKET_NAMES = [
    "UNKONWN",
    "CONNECT",
    "CONNACK",
    "PUBLISH",
    "PUBACK",
    "PUBREC", 
    "PUBREL",
    "PUBCOMP",
    "SUBSCRIBE",
    "SUBACK",
    "UNSUBSCRIBE",
    "UNSUBACK",
    "PINGREQ",
    "PINGRESP",
    "DISCONNECT",
]


PID = 0
def gen_packet_id():
    global PID
    PID = (PID + 1) % 2**16
    return PID.to_bytes(2, 'big')


class Client(object):

    def __init__(self, clientid=None, clearsession=1):
        assert clearsession in (0, 1)
        if clientid:
            assert isinstance(clientid, (bytes, str))
            if isinstance(clientid, str):
                clientid = clientid.encode('utf8')
        self.clientid = clientid
        self.clearsession = clearsession
        
        self._socket = None
        self._socket_f = None
        self._sel = selectors.DefaultSelector()

        self._out_packets = deque()
        self._unack_messages = {}
        
        self._on_connect = None
        self._on_message = None
        self._on_subscirbe = None

        self.will_flag = False
        self.username = None
        self.password = None

        self._stop = False

    def will_set(self, topic, payload=b"", qos=0, retain=False):
        assert isinstance(topic, (str, bytes))
        assert isinstance(payload, bytes)
        assert qos in (0, 1, 2)

        if isinstance(topic, str):
            topic = topic.encode('utf8')
        self.will_flag = True
        self.will_topic = topic
        self.will_message = payload
        self.will_qos = qos
        if retain:
            self.will_retain = 1
        else:
            self.will_retain = 0

    def username_passwd_set(self, username, password=None):
        assert isinstance(username, (str, bytes))
        if isinstance(username, str):
            username = username.encode('utf8')
        self.username = username

        if password:
            assert isinstance(password, (str, bytes))
            if isinstance(password, str):
                password = password.encode('utf8')
            self.password = password

    def connect(self, host, port=1883):
        if self._socket:
            raise Exception("Already connected")

        self._socket = socket.socket()
        self._socket.connect((host, port))

        fixheader_1 = b'\x10' # CONNECT package 
        fixheader_2 = b'' # remaining length, compute after

        varheder_1_6 = b'\x00\x04MQTT' # protocol name
        varheder_7 = b'\x04' # protocol level

        varheder_8 = self.clearsession<<1 # connect flags
        if self.will_flag:
            varheder_8 = varheder_8 | 0b100 | self.will_qos<<3 | self.will_retain<<4
        if self.password:
            varheder_8 = varheder_8 | 0b1000000
        if self.username:
            varheder_8 = varheder_8 | 0b10000000
        varheder_8 = bytes([varheder_8])
        varheder_9_10 = (10).to_bytes(2, 'big') # keep alive 10s

        payload_clientid = self.clientid or str(uuid1()).encode('utf8')
        payload_clientid_prefix = len(payload_clientid).to_bytes(2, 'big')
        self.clientid = payload_clientid
        remaining_length = 10+2+len(payload_clientid)
        payload = b''.join([payload_clientid_prefix, payload_clientid])

        if self.will_flag:
            # topic
            topic_prefix = len(self.will_topic).to_bytes(2, 'big')
            remaining_length += 2 + len(self.will_topic)
            # message
            message_prefix = len(self.will_message).to_bytes(2, 'big')
            remaining_length += 2 + len(self.will_message)

            payload = b''.join([payload, topic_prefix, self.will_topic,
                message_prefix + self.will_message])

        if self.username:
            prefix = len(self.username).to_bytes(2, 'big')
            remaining_length += 2 + len(self.username)
            payload = b''.join([payload, self.username])

        if self.password:
            prefix = len(self.password).to_bytes(2, 'big')
            remaining_length += 2 + len(self.password)
            payload = b''.join([payload, self.password])

        fixheader_2 = remaining_length_encode(remaining_length)
        packet = b''.join([
            fixheader_1, fixheader_2,
            varheder_1_6, varheder_7, varheder_8, varheder_9_10,
            payload])

        self._out_packets.append(packet)
        self._sel.register(self._socket, selectors.EVENT_READ)

    def disconnect(self):
        assert self._socket
        packet = b'\xe0\x00'
        self._out_packets.append(packet)
        self._sel.unregister(self._socket)

    def ping(self):
        packet = b'\xc0\x00'
        self._out_packets.append(packet)

    def publish(self, topic, payload=b'', qos=0):
        assert isinstance(topic, (str, bytes))
        assert isinstance(payload, bytes)
        assert qos in (0, 1, 2)
        assert self._socket

        if isinstance(topic, str):
            topic = topic.encode('utf8')

        fixheader_1 = bytes([0x30|qos << 1]) # PUBLISh package, dup=0, retain=0
        fixheader_2 = b'' # remaining length, compute after

        varheader_topic_prefix = len(topic).to_bytes(2, 'big')
        varheader_topic = topic

        if qos > 0:
            varheader_id = gen_packet_id()
        else:
            varheader_id = b''

        fixheader_2 = remaining_length_encode(2+len(topic)+len(varheader_id)+len(payload))
        packet = b''.join([
            fixheader_1, fixheader_2,
            varheader_topic_prefix, varheader_topic, varheader_id,
            payload])
        self._out_packets.append(packet)

        if qos == 1:
            print('wait PUBACK')
        if qos == 2:
            print('wait PUBREC')
        print('publish success')

    def subscribe(self, topic, qos=0):
        assert isinstance(topic, bytes)
        assert qos in (0, 1, 2)
        assert self._socket

        fixheader_1 = b'\x82' # SUBSCRIBE package
        fixheader_2 = b'' # remaining length, compute after

        varheader_identifier = gen_packet_id()

        payload_topic_prefix = len(topic).to_bytes(2, 'big')
        payload_topic = topic
        payload_req_qos = bytes([qos])

        fixheader_2 = remaining_length_encode(2+2+len(topic)+1)
        packet = b''.join([
            fixheader_1, fixheader_2,
            varheader_identifier,
            payload_topic_prefix, payload_topic, payload_req_qos])
        self._out_packets.append(packet)
        print('wait SUBACK')

    def unsubscribe(self, topic):
        assert self._socket
        fixheader_1 = b'\xa2' # UNSUBSCRIBE package
        fixheader_2 = b'' # remaining length, compute after

        varheader_identifier = gen_packet_id()

        payload_topic_prefix = len(topic).to_bytes(2, 'big')
        payload_topic = topic

        fixheader_2 = remaining_length_encode(2+2+len(topic))
        packet = b''.join([
            fixheader_1, fixheader_2,
            varheader_identifier,
            payload_topic_prefix, payload_topic, payload_req_qos])
        self._out_packets.append(packet)

    def loop(self, timeout=1.0):
        while len(self._out_packets) != 0:
            packet = self._out_packets.popleft()
            self.send_packet(packet)

        if self._sel.select(timeout):
            self.recv_packet()

    def loop_forever(self, timeout=1.0):
        while not self._stop:
            self.loop(timeout)

    def stop(self):
        try:
            self._socket.close()
            self._socket_f.close()
        except:
            pass
        self._stop = True
        
            
    def send_packet(self, packet):
        self._socket.sendall(packet)

    def recv_packet(self):
        if not self._socket_f:
            self._socket_f = self._socket.makefile('rb')
        r = self._socket_f.read(1)
        if r == b'':
            self._socket_f.close()
            self._socket.close()
            raise Exception("server close connection")
        r = r[0]
        type = (r & 0xf0) >> 4
        flags = r & 0x0f
        l = []
        while True:
            r = self._socket_f.read(1)[0]
            l.append(r)
            if r < 128:
                break
        remaining_length = remaining_length_decode(bytes(l))
        payload = self._socket_f.read(remaining_length)
        print("recv %s remaining_length:%d payload:%r" % (PACKET_NAMES[type], remaining_length, payload))
        if type == CONNACK:
            rc = payload[1]
            if rc != 0:
                raise Exception("Connect faild with return code %d" % rc)
            if self._on_connect:
                self._on_connect(self)
        elif type == PUBLISH:
            qos = (flags & 0b0110) >> 1
            topic_len = payload[0] * 256 + payload[1]
            topic = payload[2:2+topic_len].decode('utf-8')
            if qos == 0:
                message = payload[2+topic_len:]
                if self._on_message:
                    self._on_message(self, topic, message)
                # print("recv PUBLISH topic:%s message:%r pid:%d" % (topic, message, pid))
            elif qos == 1:
                pid = payload[2+topic_len] * 256 + payload[2+topic_len+1]
                message = payload[2+topic_len+2:]
                if self._on_message:
                    self._on_message(self, topic, message)
                self._puback(pid)
            elif qos == 2:
                pid = payload[2+topic_len] * 256 + payload[2+topic_len+1]
                message = payload[2+topic_len+2:]
                self._unack_messages[pid] = (topic, message)
                print("get publish pid:%d" % pid)
                self._pubrec(pid)
            else:
                print("wrong qos %d" % qos)
        elif type == PUBACK:
            pid = payload[0] * 256 + payload[1]
            print("recv PUBACK pid: %d" % pid)
        elif type == PUBREC:
            pid = payload[0] * 256 + payload[1]
            self._pubrel(pid)
        elif type == PUBREL:
            pid = payload[0] * 256 + payload[1]
            if self._on_message:
                topic, message = self._unack_messages.pop(pid)
                self._on_message(self, topic, message)
            self._pubcomp(pid)
        elif type == PUBCOMP:
            pid = payload[0] * 256 + payload[1]
            print("%d message complete" % pid)
        elif type == SUBACK:
            pid = payload[0] * 256 + payload[1]
        elif type == UNSUBACK:
            pid = payload[0] * 256 + payload[1]
            print("%d unsuback success" % pid)
        elif type == PINGRESP:
            print("Pong..")
            
    def _puback(self, pid):
        packet = bytes([PUBACK << 4, 2]) + pid.to_bytes(2, 'big')
        self._out_packets.append(packet)

    def _pubrec(self, pid):
        packet = bytes([PUBREC << 4, 2]) + pid.to_bytes(2, 'big')
        self._out_packets.append(packet)

    def _pubrel(self, pid):
        packet = bytes([(PUBREL << 4)|0b10, 2]) + pid.to_bytes(2, 'big')
        self._out_packets.append(packet)

    def _pubcomp(self, pid):
        packet = bytes([PUBCOMP << 4, 2]) + pid.to_bytes(2, 'big')
        self._out_packets.append(packet)

    # callbacks
    @property
    def on_connect(self):
        return self._on_connect

    @on_connect.setter
    def on_connect(self, func):
        self._on_connect = func

    @property
    def on_message(self):
        return self._on_message

    @on_message.setter
    def on_message(self, func):
        self._on_message = func

    @property
    def on_subscribe(self):
        return self._on_subscirbe

    @on_subscribe.setter
    def on_subscribe(self, func):
        self._on_subscirbe = func
        
        
def remaining_length_encode(x):
    '''Return bytes representation.'''
    if x > 268435455:
        raise ValueError('remaining length too larger')
    result = [] 
    while True:
        x, b = divmod(x, 128)
        if x > 0:
            b = b | 128
        result.append(b) 
        if x == 0:
            break
    return bytes(result) 


def remaining_length_decode(x):
    if len(x) >= 4:
        raise ValueError('remaining length too large')
    multiplier = 1
    value = 0
    for b in x:
        value += (b & 127) * multiplier
        multiplier *= 128
    return value

def assert_remaining_length(x):
    assert x == remaining_length_decode(remaining_length_encode(x))



if __name__ == '__main__':
    assert remaining_length_encode(0) == bytes([0])
    assert remaining_length_encode(23) == bytes([23])
    assert remaining_length_encode(127) == bytes([127])
    assert remaining_length_encode(128) == bytes([0x80, 0x01])
    assert remaining_length_encode(321) == bytes([193, 2])
    assert remaining_length_encode(16383) == bytes([0xff, 0x7f])
    assert remaining_length_encode(2097152) == bytes([0x80, 0x80, 0x80, 0x01])
    assert_remaining_length(0)
    assert_remaining_length(1)
    assert_remaining_length(127)
    assert_remaining_length(888888)
    assert_remaining_length(128)

    def on_message(client, topic, message):
        print("got %s  message: %s" % (topic, message))
        if message.startswith(b'cool'):
            client.publish(topic, b'you cool too!!')

    import time
    c = Client()
    c.on_message = on_message
    c.will_set(b'will', b'bye bye')
    c.connect('localhost')
    c.subscribe(b'a/b', 2)
    # c.publish(b'a/b', b'hello world')
    # c.send_packet()
    # c.publish(b'a/b', b'hello world1', qos=1)
    # c.send_packet()
    # time.sleep(1)
    # c.publish(b'a/b', b'hell', qos=2)
    # c.send_packet()
    c.loop_forever()
