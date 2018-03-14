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
        self.client_id = None
        self._pids = []
        self._unack = {}
        self._seen_qos2 = []
        self._subscribe_topic = []

        self.keepalive = 0
        self._alive = False
        self._stop = False

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
        logger.debug("[%s] Sending PUBLISH. topic:%s", self.client_id, topic)
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
            logger.warning("[%s] client error: %s", self.client_id, e)
        finally:
            try:
                clients.remove(self)
            except ValueError:
                pass
            for topic in self._subscribe_topic:
                del subscriptions[topic][self]
                self.s.close()

    def stop(self):
        logger.info("[%s] stopping client", self.client_id)
        self.s.close()
        self._stop = True

    async def wait_connect(self):
        r = await asyncio.wait_for(loop.sock_recv(self.s, 1), self.timeout)
        if r == b'':
            logger.info("[%s] client close connection", self.client_id)
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
        if remaining_length < 10:
            raise Exception("CONNECT packet too small")
        payload = await loop.sock_recv(self.s, remaining_length)
        if payload[:6] != b"\x00\x04MQTT":
            raise Exception("Protocol name not match")
        if payload[6] != 4:
            logger.warning("unacceptable protocol level %d", payload[6])
            return False
        connect_flags = payload[7]
        self.keepalive = payload[8]*256 + payload[9]
        if self.keepalive > 0:
            asyncio.ensure_future(self.do_keepalive())
        client_id_len = payload[10]*256 + payload[11]
        client_id = payload[12:12+client_id_len].decode('utf8')
        self.client_id = client_id
        logger.info("New client %s connected. connect_flags:%s", client_id, bin(connect_flags))
        connack = b'\x20\x02\x00\x00'
        await loop.sock_sendall(self.s, connack)
        return True

    async def process(self):
        while not self._stop:
            r = await loop.sock_recv(self.s, 1)
            if r == b'':
                self.s.close()
                logger.info("[%s] client close connection", self.client_id)
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

            self._alive = True
            await getattr(self, 'handle_' + PACKET_NAMES[type])(flags, payload)

    async def handle_SUBSCRIBE(self, flags, payload):
        assert flags == 2
        pid, payload = payload[:2], payload[2:]
        topics = []
        while payload:
            l = payload[0] * 256 + payload[1]
            topic = payload[2:2+l].decode('utf8')
            qos = payload[2+l]
            logger.info("[%s] subscribe %s %d", self.client_id, topic, qos)
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
        logger.debug("[%s] recv PUBLISH topic:%s pid:%d", self.client_id, topic, pid)

    async def handle_PUBACK(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        self._pids.remove(pid)
        del self._unack[pid]

    async def handle_PUBREC(self, flags, payload):
        pid = payload[0] * 256 + payload[1]
        pubrel = b'\x62\x02' + payload
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

    async def do_keepalive(self):
        while not self._stop:
            await asyncio.sleep(self.keepalive * 1.5)
            if not self._alive:
                logger.info("[%s] not alive", self.client_id)
                self.stop()
            self._alive = False


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
                c2qos = subscriptions[t].copy()
                for c, q in c2qos.items():
                    if qos <= q:
                        try:
                            await c.send(message, topic, qos)
                        except Exception as e:
                            logger.warning("Sending message error: %s", e)
                            c.close()


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
