"""Library to handle connection with Ambiclimate API."""
import asyncio
import logging

import aiohttp
import async_timeout

DEFAULT_TIMEOUT = 10
API_ENDPOINT = 'https://api.ambiclimate.com/api/v1/'

_LOGGER = logging.getLogger(__name__)


class Ambiclimate:
    """Class to comunicate with the Ambiclimate api."""

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
        self._devices_info = []

    async def request(self, command, params, retry=3, get=True):
        """Request data."""
        headers = {
            "accept": "application/json",
            'Authorization': 'Bearer ' + self._access_token
        }

        url = API_ENDPOINT + command

        try:
            with async_timeout.timeout(self._timeout):
                if get:
                    resp = await self.websession.get(url, headers=headers, params=params)
                else:
                    resp = await self.websession.post(url, headers=headers, params=params)
        except asyncio.TimeoutError:
            if retry < 1:
                _LOGGER.error("Timed out sending command to Ambiclimate: %s", command)
                return None
            return await self.request(command, params, retry - 1)
        except aiohttp.ClientError:
            _LOGGER.error("Error sending command to Ambiclimate: %s", command, exc_info=True)
            return None

        result = await resp.json()
        status = result.get('status')
        if status is not None:
            if status == 'ok':
                return True
            return False

        return result

    async def find_devices(self):
        """Get users Ambi Climate device information."""
        res = await self.request('devices', {})
        self._devices_info = res.get('data', [])
        return bool(self._devices_info)

    def get_devices(self):
        """Get users Ambi Climate device information."""
        res = []
        for device in self._devices_info:
            res.append(AmbiclimateDevice(device.get('room_name'),
                                         device.get('location_name'),
                                         device.get('device_id'),
                                         self))
        return res


class AmbiclimateDevice:
    """Instance of Ambiclimate device."""

    def __init__(self, room_name, location_name, device_id, ambiclimate_control):
        """Initialize the Ambiclimate device class."""
        self._room_name = room_name
        self._location_name = location_name
        self._device_id = device_id
        self._ambiclimate_control = ambiclimate_control

    async def request(self, command, params, retry=3):
        """Request data."""
        params['room_name'] = self._room_name
        params['location_name'] = self._location_name
        return await self._ambiclimate_control.request(command, params, retry)

    async def set_power_off(self, multiple=False):
        """Power off your AC."""
        return await self.request('device/power/off', {'multiple': multiple})

    async def set_comfort_mode(self, multiple=False):
        """Enable Comfort mode on your AC."""
        return await self.request('device/mode/comfort', {'multiple': multiple})

    async def set_comfort_feedback(self, value):
        """Send feedback for Comfort mode."""
        valid_comfort_feedback = ['too_hot', 'too_warm', 'bit_warm', 'comfortable',
                                  'bit_cold', 'too_cold', 'freezing']
        if value not in valid_comfort_feedback:
            _LOGGER.error("Invalid comfort feedback")
            return
        return await self.request('user/feedback', {'value': value})

    async def set_away_mode_temperature_lower(self, value, multiple=False):
        """Enable Away mode and set an lower bound for temperature."""
        return await self.request('device/mode/away_temperature_lower',
                                  {'multiple': multiple, 'value': value})

    async def set_away_mode_temperature_upper(self, value, multiple=False):
        """Enable Away mode and set an upper bound for temperature."""
        return await self.request('device/mode/away_temperature_upper',
                                  {'multiple': multiple, 'value': value})

    async def set_away_humidity_upper(self, value, multiple=False):
        """Enable Away mode and set an upper bound for humidity."""
        return await self.request('device/mode/away_humidity_upper',
                                  {'multiple': multiple, 'value': value})

    async def set_temperature_mode(self, value, multiple=False):
        """Enable Temperature mode on your AC."""
        return await self.request('device/mode/temperature',
                                  {'multiple': multiple, 'value': value})

    async def get_sensor_temperature(self):
        """Get latest sensor temperature data."""
        res = await self.request('device/sensor/temperature', {})
        return res.get('value')

    async def get_sensor_humidity(self):
        """Get latest sensor humidity data."""
        res = await self.request('device/sensor/humidity', {})
        return res.get('value')

    async def get_sensor_mode(self):
        """Get Ambi Climate's current working mode."""
        res = await self.request('device/mode', {})
        return res.get('mode')

    async def get_ir_feature(self):
        """Get Ambi Climate's appliance IR feature."""
        return await self.request('device/ir_feature', {})
