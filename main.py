from utils import common
import sys, logging

now = common.now
is_back_test = False
start_year = now.year
end_year = now.year
log_level = "warning"


def main():
    try:
        common.get_argumets()
        common.setup_log_config(log_level)
        logger = logging.getLogger(__name__)
        logger.debug("This is a debug")
        logger.info("This is a info")
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    print("run in main module")
    sys.exit(main())
