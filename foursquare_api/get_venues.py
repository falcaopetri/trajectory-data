import logging
from my_requests import Requests
import os
import time
import json
import sys
import configparser
import pandas as pd


CONFIG_FILE = sys.argv[1]

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

DATA_DIR = os.path.join(config['GENERAL']['DATA_DIR'], '')
VENUE_ENDPOINT = config['FOURSQUARE_API']['VENUE_ENDPOINT']
VERSION = config['FOURSQUARE_API']['V']
DEAD_VENUES = config['FOURSQUARE_API']['DEAD_VENUES'].split(',')

# (Client ID, Client Secret)
API_KEYS = [pair.split(',') for pair in config['FOURSQUARE_API']['KEYS'].split(';')]
ACTIVE_KEY = 0

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

logging.basicConfig()
logger = logging.getLogger("fq_api")
logger.setLevel(logging.INFO)

req = Requests()
req.config(client_id=API_KEYS[ACTIVE_KEY][0],
           client_secret=API_KEYS[ACTIVE_KEY][1])

fetched = 0
skipped = 0


def waitToNextMidnight():
    t = time.localtime()
    t = time.mktime(t[:3] + (0, 0, 0) + t[6:])
    logger.info('Sleeping until midnight of tomorrow... ')
    time.sleep(t + 24*3600 - time.time() + 10)
    logger.info('Sleeping until midnight of tomorrow... WOKE UP!')


def fetch_venues():
    global skipped, fetched, ACTIVE_KEY
    venues = pd.read_csv(config['GENERAL']['VENUE_FILE'])

    for i, row in venues.iterrows():
        foursquare_id = row[0]
        file = foursquare_id + '.json'
        venue_fetched = False

        if os.path.isfile(DATA_DIR + file) or foursquare_id in DEAD_VENUES:
            skipped += 1
            logger.info('Venue ' + foursquare_id + ' already retrieved or dead' +
                           ' (Skipped = ' + str(skipped) + ')!')
            continue

        rsp = req.get(VENUE_ENDPOINT.replace('VENUE_ID', foursquare_id),
                      named_params=['v=' + VERSION])
        venue_fetched = req.validate(rsp)

        while not venue_fetched:
            if 'is invalid for venue id' in rsp['meta']['errorDetail']:
                break

            if req._status not in [500, 502]:
                ACTIVE_KEY = (ACTIVE_KEY + 1) % len(API_KEYS)
                req.config(client_id=API_KEYS[ACTIVE_KEY][0],
                           client_secret=API_KEYS[ACTIVE_KEY][1])
                logger.warning('Active API key changed to ' +
                           str(ACTIVE_KEY) + '.')
                time.sleep(60)

            if ACTIVE_KEY == 0:  # All keys are done, sleep until next day
                logger.warning('All API keys have reached the calls limit!')
                logger.info('Summary: Fetched = ' + str(fetched) +
                           '\tSkipped = ' + str(skipped))
                waitToNextMidnight()

            rsp = req.get(VENUE_ENDPOINT.replace('VENUE_ID', foursquare_id),
                          named_params=['v=' + VERSION])
            venue_fetched = req.validate(rsp)

        if venue_fetched:
            logger.info('Retrieving venue ' + foursquare_id + '.')
            with open(DATA_DIR + file, 'w') as outfile:
                json.dump(rsp, outfile)
        else:
            logger.warning('Venue ' + foursquare_id + ' skipped (invalid ID or something unexpected).')

        fetched += 1 if venue_fetched else 0
        time.sleep(2)

while True:
    try:
        fetch_venues()
        break
    except Exception as e:
        logger.error(str(e))
        logger.warning('Waiting 60 seconds to restart...')
        time.sleep(60)
