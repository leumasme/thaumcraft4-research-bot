import logging
import sys

log = logging.getLogger("bot")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))
# log.setLevel(logging.WARN)