"""Library to handle connection with Ambiclimate API."""
import asyncio
import logging

import aiohttp
import async_timeout
from gql import gql
from graphql.language.printer import print_ast
from graphql_subscription_manager import SubscriptionManager

DEFAULT_TIMEOUT = 10
API_ENDPOINT = 'https://api.ambiclimate.com/api/v1/'

_LOGGER = logging.getLogger(__name__)


class Ambiclimate:
    """Class to comunicate with the Ambiclimate api."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, access_token,
                 timeout=DEFAULT_TIMEOUT,
                 websession=None):
        """Initialize the Ambiclimate connection."""
        if websession is None:
            async def _create_session():
                return aiohttp.ClientSession()
            loop = asyncio.get_event_loop()
            self.websession = loop.run_until_complete(_create_session())
        else:
            self.websession = websession
        self._timeout = timeout
        self._access_token = access_token
        self._devices = []

   async def request(self, command, payload, retry=3):
        """Request data."""
         headers = {
            "accept": "application/json",
            'Authorization': 'Bearer ' + self._access_token
        }

        url = API_ENDPOINT + command

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self.websession.get(url, headers=headers)
        except asyncio.TimeoutError:
            if retry < 1:
                _LOGGER.error("Timed out sending command to Ambiclimate: %s", command)
                return None
            return await self.request(command, payload, retry - 1)
        except aiohttp.ClientError:
            _LOGGER.error("Error sending command to Ambiclimate: %s", command, exc_info=True)
            return None

        result = await resp.json()
        return result


class AmbiclimateDevice:
    """Instance of Ambiclimate device."""

    def __init__(self, room_name, location_name, ambiclimate_control):
        """Initialize the Ambiclimate device class."""
        self._ambiclimate_control = ambiclimate_control
        self._room_name = room_name
        self._location_name = location_name
