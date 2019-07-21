import logging
import redis
from os import getenv as env
from os.path import join, dirname, abspath
from flask import Flask
from dotenv import load_dotenv
from privex.loghelper import LogHelper
from privex.helpers import empty, env_bool
from privex.steemengine import SteemEngineToken

flask = Flask(__name__)
cf = flask.config

load_dotenv()

DEBUG = cf['DEBUG'] = env_bool('DEBUG', False)

cf['FLASK_ENV'] = 'development' if DEBUG else 'production'

#####
#
# SteemEngine RPC configuration
#
#####
SE_HOST = cf['SE_HOST'] = env('SE_HOST', 'api.steem-engine.com')
SE_URL = cf['SE_URL'] = env('SE_URL', '/rpc/contracts')
SE_NET_ACC = cf['SE_NET_ACC'] = env('SE_NET_ACC', 'ssc-mainnet1')
SE_SSL = cf['SE_SSL'] = env_bool('SE_SSL', True)
SE_PORT = cf['SE_PORT'] = int(env('SE_PORT', 443 if cf['SE_SSL'] else 80))

CACHE_TIME = cf['CACHE_TIME'] = int(env('CACHE_TIME', 600))
"""Amount of time (in seconds) to cache token data for. Default: 600 seconds (10 minutes)"""

BASE_DIR = dirname(abspath(__file__))

LOG_DIR = join(BASE_DIR, 'logs')

LOG_LEVEL = cf['LOG_LEVEL'] = env('LOG_LEVEL')
LOG_LEVEL = logging.getLevelName(str(LOG_LEVEL).upper()) if not empty(LOG_LEVEL) else None
LOG_LEVEL = (logging.DEBUG if DEBUG else logging.INFO) if empty(LOG_LEVEL) else LOG_LEVEL


# This default LOG_FORMATTER results in messages that look like this:
#
#   [2019-03-26 20:21:01,798]: payments.management.commands.convert_coins -> handle : INFO :: Coin converter
#    and deposit validator started
#
LOG_FORMATTER = logging.Formatter('[%(asctime)s]: %(name)-55s -> %(funcName)-20s : %(levelname)-8s:: %(message)s')

lh = LogHelper('imageproxy', handler_level=LOG_LEVEL, formatter=LOG_FORMATTER)
lh.add_timed_file_handler(join(LOG_DIR, 'error.log'), level=logging.WARNING)
lh.add_timed_file_handler(join(LOG_DIR, 'debug.log'))
lh.add_console_handler()

REDIS_HOST = cf['REDIS_HOST'] = env('REDIS_HOST', 'localhost')
REDIS_PORT = cf['REDIS_PORT'] = int(env('REDIS_PORT', 6379))
REDIS_DB = cf['REDIS_DB'] = int(env('REDIS_DB', 0))

__STORE = {}


def get_redis() -> redis.Redis:
    """Get a Redis connection object. Create one if it doesn't exist."""
    if 'redis' not in __STORE:
        __STORE['redis'] = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    return __STORE['redis']


def get_steemengine() -> SteemEngineToken:
    if 'steemengine' not in __STORE:
        __STORE['steemengine'] = SteemEngineToken(
            network_account=SE_NET_ACC, hostname=SE_HOST, port=SE_PORT, ssl=SE_SSL, url=SE_URL
        )
    return __STORE['steemengine']
