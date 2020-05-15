import asyncio
import logging
import signal
from argparse import RawDescriptionHelpFormatter
from typing import Any, Dict, Optional

from tap import Tap

from opcua_webhmi_bridge.config import Config
from opcua_webhmi_bridge.opcua import UAClient
from opcua_webhmi_bridge.pubsub import Hub
from opcua_webhmi_bridge.websocket import WebsocketServer


async def shutdown(
    loop: asyncio.AbstractEventLoop, sig: Optional[signal.Signals] = None
) -> None:
    """Cleanup tasks tied to the service's shutdown"""
    if sig:
        logging.info("Received exit signal %s", sig.name)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    logging.info("Waiting for %s outstanding tasks to finish...", len(tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if not isinstance(result, asyncio.CancelledError) and isinstance(
            result, Exception
        ):
            logging.error("Exception occured during shutdown: %s", result)
    loop.stop()


def handle_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    # context["message"] will always be there; but context["exception"] may not
    try:
        exc: Exception = context["exception"]
    except KeyError:
        logging.error("Caught exception: %s", context["message"])
    else:
        logging.error("Caught exception %s: %s", exc.__class__.__name__, exc)
    logging.info("Shutting down...")
    asyncio.create_task(shutdown(loop))


def main() -> None:
    class ArgumentParser(Tap):
        verbose: bool = False  # Be more verbose (print debug informations)

        def add_arguments(self) -> None:
            self.add_argument("-v", "--verbose")

    parser = ArgumentParser(
        description="Bridge between OPC-UA server and web-based HMI",
        epilog=f"Environment variables:\n{Config.generate_help()}",
        formatter_class=RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s:%(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    if not args.verbose:
        for logger in [
            "asyncua.common.subscription",
            "asyncua.client.ua_client.UASocketProtocol",
        ]:
            logging.getLogger(logger).setLevel(logging.ERROR)

    config = Config()
    hub = Hub()
    ws_server = WebsocketServer(config, hub)
    opc_client = UAClient(config, hub)

    loop = asyncio.get_event_loop()
    loop.set_debug(args.verbose)

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(loop, sig=s))
        )
    loop.set_exception_handler(handle_exception)

    try:
        loop.run_until_complete(ws_server.start_server)
        loop.create_task(opc_client.task())
        loop.run_forever()
    finally:
        loop.close()
        logging.info("Shutdown successfull")


if __name__ == "__main__":
    main()
