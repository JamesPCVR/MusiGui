import logging
import sys

import interface


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        filename="debug.log", filemode="wt+", encoding="utf-8", level=logging.DEBUG
    )

    # https://stackoverflow.com/questions/6234405
    def my_excepthook(exc_type, exc_value, exc_traceback):
        logger.critical(
            "Uncaught Exception:", exc_info=(exc_type, exc_value, exc_traceback)
        )
        print("A fatal error occured.")
        sys.exit(1)

    sys.excepthook = my_excepthook

    interface.start_app(500, 700)

if __name__ == "__main__":
    main()
