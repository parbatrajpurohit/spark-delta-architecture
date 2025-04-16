import signal
import time

from logging import getLogger

import uvicorn

from app.api_endpoints import Api

# Global logger initializations
logger = getLogger()


api = Api(5001)


if __name__ == '__main__':
    uvicorn.run(api.app, host="0.0.0.0", port=8000)

    # stop = False
    #
    # def handle_signal(signum, frame):
    #     global stop
    #     stop = True
    #     logger.info(f"Caught signal {signum}, shutting down.")
    #
    #
    # signal.signal(signal.SIGTERM, handle_signal)
    # signal.signal(signal.SIGINT, handle_signal)
    #
    # try:
    #     api.start()
    #     # api.server.run()
    #
    #     while not stop:
    #         time.sleep(1)
    #
    # finally:
    #     api.shutdown()
    #     # api.server.shutdown()
    #     logger.info("Done")