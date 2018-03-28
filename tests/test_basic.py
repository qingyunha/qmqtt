import unittest
import time
import subprocess
import threading

from .mqttc import Client

server = None

def setUpModule():
    global server
    server = subprocess.Popen(["python", "-m", "qmqtt", "-v"])
    time.sleep(1)


def tearDownModule():
    server.terminate()
    server.wait()


class TestMqtt(unittest.TestCase):

    def test_subpub(self):
        c1 = Client("c111111")
        c2 = Client("c222222")
        c1.connect('localhost')
        c2.connect('localhost')
        c1.subscribe(b'a/b', 2)
        c2.subscribe(b'a/b', 2)
        t1 = threading.Thread(target=c1.loop_forever)
        t2 =threading.Thread(target=c2.loop_forever)
        t1.start()
        t2.start()
        time.sleep(1)
        c1.publish(b'a/b', b'hello world1', qos=1)
        c1.publish(b'a/b', b'hello world12342', qos=0)
        c2.publish(b'a/b', b'hello world1', qos=2)
        time.sleep(1)
        print("============== client stop")
        c1.stop()
        c2.stop()
        t1.join()
        t2.join()


if __name__ == '__main__':
    unittest.main()