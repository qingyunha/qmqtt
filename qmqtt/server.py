import socket
import asyncio
import logging
import datetime
import collections
import logging


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


logger = logging.getLogger("mqtt")
loop = asyncio.get_event_loop()
clients = []
messages = asyncio.Queue()
subscriptions = collections.defaultdict(dict)


class Client:

    def __init__(self, socket, timeout=None):
        self.s = socket
        self.s.setblocking(False)
        self.timeout = timeout
        self._pids = []
        self._unack = {}
        self._seen_qos2 = []
        self._subscribe_topic = []

    def gen_packet_id(self):
        l = len(self._pids)
        if l == 0:
            self._pids.append(1)
            return 1
        if l > 65535:
            raise Exception("No pid can use")
        i = 1
        for pid in self._pids:
            if i < pid:
                break
            i += 1
        self._pids.append(i)
        self._pids.sort()
        return i

    async def send(self, message, topic, qos):
        fixheader_1 = bytes([0x30|qos << 1]) # PUBLISh package, dup=0, retain=0
        fixheader_2 = b'' # remaining length, compute after

        varheader_topic_prefix = len(topic).to_bytes(2, 'big')
        varheader_topic = topic.encode('utf8')

        if qos > 0:
            pid = self.gen_packet_id()
            varheader_id = pid.to_bytes(2, 'big')
        else:
            varheader_id = b''

        fixheader_2 = remaining_length_encode(2+len(topic)+len(varheader_id)+len(message))
        packet = b''.join([
            fixheader_1, fixheader_2,
            varheader_topic_prefix, varheader_topic, varheader_id,
            message])
        logger.debug("Sending PUBLISH. topic:%s pid:%d", topic, pid)
        if qos > 0:
            self._unack[pid] = packet
        await loop.sock_sendall(self.s, packet)

    async def start(self):
        try:
            if await self.wait_connect():
                await self.process()
        except asyncio.TimeoutError:
           logger.warning("client timeout")
        except Exception as e:
           logger.warning("client error %s", e)
        finally:
            clients.remove(self)
            for topic in self._subscribe_topic:
                del subscriptions[topic][self]
            self.s.close()

    async def wait_connect(self):
        r = await asyncio.wait_for(loop.sock_recv(self.s, 1), self.timeout)
        if r == b'':
            logger.info("client close connection")
            return False
        r = r[0]
        type = (r & 0xf0) >> 4
        flags = r & 0x0f
        if type != CONNECT:
            logger.warning("Connect faild. unexpect packet")
            return False
        l = []
        while True:
            r = await loop.sock_recv(self.s, 1)
            r = r[0]
            l.append(r)
            if r < 128:
                break
        remaining_length = remaining_length_decode(bytes(l))
        payload = await loop.sock_recv(self.s, remaining_length)
        logger.info("New client connected")
        connack = b'\x20\x02\x00\x00'
        await loop.sock_sendall(self.s, connack)
        return True

    async def process(self):
        while True:
            r = await loop.sock_recv(self.s, 1)
            if r == b'':
                self.s.close()
                logger.info("client close connection")
                return False
            r = r[0]
            type = (r & 0xf0) >> 4
            flags = r & 0x0f
            l = []
            while True:
                r = await loop.sock_recv(self.s, 1)
                r = r[0]
                l.append(r)
                if r < 128:
                    break
            remaining_length = remaining_length_decode(bytes(l))
            if remaining_length:
                payload = await loop.sock_recv(self.s, remaining_length)
            else:
                payload = b''

            await getattr(self, 'handle_' + PACKET_NAMES[type])(flags, payload)

    async def handle_SUBSCRIBE(self, flags, payload):
        assert flags == 2
        pid, payload = payload[:2], payload[2:]
        topics = []
        while payload:
            l = payload[0] * 256 + payload[1]
            topic = payload[2:2+l].decode('utf8')
            qos = payload[2+l]
            logger.info("subscribe %s %d", topic, qos)
            topics.append((topic, qos))
            subscriptions[topic][self] = qos
            self._subscribe_topic.append(topic)
            payload = payload[3+l:]
        suback = b'\x90' + remaining_length_encode(2+len(topics)) + pid
        returncodes = bytes([t[1] for t in topics])
        suback = suback + returncodes
        await loop.sock_sendall(self.s, suback)

    async def handle_PUBLISH(self, flags, payload):
        qos = (flags & 0b0110) >> 1
        dup = (flags & 0b1000) >> 3
        retain = flags & 0b0001
        topic_len = payload[0] * 256 + payload[1]
        topic = payload[2:2+topic_len].decode('utf-8')
        if qos == 0:
            pid = -1
            message = payload[2+topic_len:]
            await messages.put((message, topic, qos))
        else:
            pid = payload[2+topic_len] * 256 + payload[2+topic_len+1]
            message = payload[2+topic_len+2:]
            if qos == 1:
                await messages.put((message, topic, qos))
                puback = bytes([PUBACK << 4, 2]) + pid.to_bytes(2, 'big')
                await loop.sock_sendall(self.s, puback)
            elif qos == 2:
                if pid not in self._seen_qos2:
                    self._seen_qos2.append(pid)
                    await messages.put((message, topic, qos))
                pubrec = b'\x50\x02' + pid.to_bytes(2, 'big')
                await loop.sock_sendall(self.s, pubrec)
        logger.debug("recv PUBLISH topic:%s pid:%d", topic, pid)

    async def handle_PUBACK(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        self._pids.remove(pid)
        del self._unack[pid]

    async def handle_PUBREC(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        pubrel = b'\x60\x02' + payload
        self._unack[pid] = pubrel
        await loop.sock_sendall(self.s, pubrel)

    async def handle_PUBREL(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        self._seen_qos2.remove(pid)
        pubcomp = b'\x70\x02' + payload
        await loop.sock_sendall(self.s, pubcomp)

    async def handle_PUBCOMP(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        self._pids.remove(pid)
        del self._unack[pid]

    async def handle_DISCONNECT(self, *_):
        pass

    async def handle_PINGREQ(self, *_):
        await loop.sock_sendall(self.s, b'\xd0\x00')


def remaining_length_decode(x):
    if len(x) >= 4:
        raise ValueError('remaining length too large')
    multiplier = 1
    value = 0
    for b in x:
        value += (b & 127) * multiplier
        multiplier *= 128
    return value


def remaining_length_encode(x):
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


async def forwarder():
    while True:
        message, topic, qos = await messages.get()
        for t in subscriptions:
            if t == topic:
                for c, q in subscriptions[t].items():
                    if qos <= q:
                        asyncio.ensure_future(c.send(message, topic, qos))


async def server(host="localhost", port=1883, timeout=None):
    s = socket.socket()
    s.bind((host, port))
    s.listen()
    s.setblocking(False)
    while True:
        conn, address = await loop.sock_accept(s)
        logger.info("New connection from %s", address)
        c = Client(conn, timeout)
        asyncio.ensure_future(c.start())
        clients.append(c)