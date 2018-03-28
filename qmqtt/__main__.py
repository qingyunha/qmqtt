import argparse
import logging
import asyncio

from qmqtt.server import server, forwarder


def main():
    parser = argparse.ArgumentParser(description="mqtt server")
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=1883)
    parser.add_argument("-t", "--timeout", type=int, default=5)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("mqtt")
    logger.setLevel(logging.INFO)
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(forwarder())
    logger.info("Start server on %s:%d", args.host, args.port)
    loop.run_until_complete(server(args.host, args.port, args.timeout))


if __name__ == '__main__':
    main()
