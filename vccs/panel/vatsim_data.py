"""
HErO ACARS
Copyright (C) 2022 SNET Technical Solutions Ltd
"""

# Standard library imports
from ctypes import c_float
import json
import math
import pandas as pd
import requests
import urllib

# Third party imports
from loguru import logger

class Vatsim:
    """Class for various VATSIM functions"""

    def __init__(self):
        # get the most up-to-date URLs from status.vatsim.net
        vatsim_servers = self.url_get_json("https://status.vatsim.net/status.json")

        logger.debug("VATSIM server response okay")
        logger.trace(vatsim_servers)

        # json output from status.vatsim.net/status.json is sub-divided by data, user and metar. only data has further sub-divisions.
        data = vatsim_servers["data"]
        self.v3_url = data["v3"][0]
        self.transceivers_url = data["transceivers"][0]
        self.servers_url = data["servers"][0]
        self.user_url = vatsim_servers["user"]
        self.metar_url = vatsim_servers["metar"]

        # store a static API address
        self.vatsim_api = "https://api.vatsim.net/api/map_data/"
    
    @staticmethod
    def url_get_json(url):
        """Requests a json page and returns the output"""
        response = requests.get(url, {"Content-type": "application/json"})
        return response.json()

    def metar(self, icao=False):
        """pull the metar for a given aerodrome"""
        if icao:
            url = f"{self.metar_url}?id={icao}"
            logger.debug("METAR URL {}", url)
            try:
                response = urllib.request.urlopen(url)
                for line in response:
                    print(line.decode("utf-8"))
                return True
            except:
                print("No METAR available")
                logger.info("No METAR found at {}", url)
                return False
        else:
            print("No METAR available")
            logger.error("No ICAO code for METAR was provided")
            return False

    def get_controller(self, match_string:int=0):
        """Gets the details of a live controller"""
        # download the json file listing all connected users
        controllers = self.url_get_json(self.v3_url)
        ###controllers = json.load(open('/var/www/vccs.vnpas.uk/test.json'))
        # filter the results for controllers and then dump in a pandas df
        df = pd.json_normalize(controllers, record_path=["controllers"])
        drop_cols = [
            "name",
            "visual_range",
            "text_atis",
            "rating",
            "server",
        ]
        df = df.drop(labels=drop_cols, axis=1)
        # filter out all of the observers
        df = df.loc[df["facility"] > 1]
        # filter by the cid we're trying to find
        if match_string != 0:
            df = df.loc[df["cid"] == match_string]
            return df.iloc[0]["callsign"]
        else:
            output = []
            for index, row in df.iterrows():
                output.append(row["callsign"])
            return output
    
    @staticmethod
    def assign_position_number(suffix):
        """
        Assigns a numerical value to a position\n
        0 = ATIS
        1 = DEL
        2 = GND
        3 = TWR
        4 = APP
        5 = CTR
        """
        if suffix == "ATIS":
            return 0
        elif suffix == "DEL":
            return 1
        elif suffix == "GND":
            return 2
        elif suffix == "TWR":
            return 3
        elif suffix == "APP":
            return 4
        elif suffix == "CTR":
            return 5
