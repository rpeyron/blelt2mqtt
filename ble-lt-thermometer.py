import asyncio
import datetime
from functools import partial
from typing import Optional
import json
import re

from bleak import BleakScanner, BleakClient
from bleak.exc import BleakDBusError
import paho.mqtt.publish as publish

import config
import const

# Install requirements :
# pip3 install -r requirements.txt
#
# Edit config in config.py


# The UUID of LT Thermometer v3 & v4 protocol
service_uuid = "0000FFE5-0000-1000-8000-00805f9b34fb"
notify_uuid = "0000FFE8-0000-1000-8000-00805f9b34fb"
char_uuid = "00002902-0000-1000-8000-00805f9b34fb"

class Log:
    """
    Simple logging class.
    Basically just prints messages with timestamp prepended, but is a start on a more flexible approach
    """
    @staticmethod
    def getLogLevel(level: str) -> int:
        """
        Return log level as int as defined in constants file.

        :param level:   Log level as string
        :type level:    str
        :return:
        :rtype:         int
        """
        ll = const.LOG_LEVELS.get(level)
        if not ll:
            ll = const.LOG_LEVELS.get("INFO")

        return ll

    @staticmethod
    def msg(msg, device_name: str = None, level: str = "INFO"):
        """
        Output a log message with prepended timestamp and device name.
        Currently just prints the message.

        :param msg:             Message to output
        :type msg:              Any
        :param device_name:     Device name to prepend (optional)
        :type device_name:      str
        :param level:           Log level of message, ERROR|WARNING|NOTICE|INFO|DEBUG, default: INFO (optional)
        :type level:            str
        :return:
        """
        # Do not log message if message level is greater than user-configured level
        if Log.getLogLevel(level) > Log.getLogLevel(config.LOG_LEVEL):
            return

        if len(msg) <= 0:
            return
        msg = f": {msg}"

        # Prepend device.name when given
        if device_name and len(device_name) > 0:
            msg = f" [{device_name}]{msg}"

        # Add timestamp to message
        msg = f"{datetime.datetime.now()} [{level}]{msg}"

        # Just print message for now
        print(msg)

class Device:
    """
    Device class.
    Acts as object holding device configuration
    """
    _name: str = ""
    custom_name: Optional[str] = ""
    _safe_name: str = ""
    mac: str = ""
    wait: int = 30
    _uniq_id = ""
    domoticz_idx: Optional[int] = 0

    def __init__(self, options: dict):
        for option, value in options.items():
            if not hasattr(self, option):
                continue

            setattr(self, option, value)

        self.uniq_id = self.mac

    @property
    def name(self) -> str:
        if self.custom_name:
            return self.custom_name
        elif self._name:
            return self._name

        return self.mac

    @name.setter
    def name(self, name: str):
        self._name = name

    @property
    def safe_name(self) -> str:
        if not self._safe_name:
            self._safe_name = self._name
        return self._safe_name

    @safe_name.setter
    def safe_name(self, name: str):
        self._safe_name = re.sub('[^a-zA-Z0-9_]', '', name)

    @property
    def uniq_id(self) -> str:
        return self._uniq_id

    @uniq_id.setter
    def uniq_id(self, address: str):
        self._uniq_id = config.MQTT_PREFIX[:-1] + address.replace(":", "")

"""
MQTT functions
"""
def get_topic_state(device: Device) -> str:
    return config.MQTT_PREFIX + device.safe_name + "/state"

def get_topic_discovery(device: Device) -> str:
    return config.MQTT_DISCOVERY_PREFIX + f"device/{device.safe_name}/config"

def mqtt_send_discovery(device: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        message = {
            "device": {
                "ids": device.safe_name,
                "name": device.name,
            },
            "origin": {
                "name": "blelt2mqtt",
                "sw_version": const.BLELT2MQTT_VERSION,
                "support_url": "https://github.com/rpeyron/blelt2mqtt"
            },
            "components": {
                f"{device.safe_name.lower()}_temperature1": {
                    "platform": "sensor",
                    "device_class": "temperature",
                    "unit_of_measurement": "°C",
                    "value_template": "{{ value_json.temperature}}",
                    "unique_id": device.safe_name + "_t",
                },
                f"{device.safe_name.lower()}_humidity1": {
                    "platform": "sensor",
                    "device_class": "humidity",
                    "unit_of_measurement": "%",
                    "value_template": "{{ value_json.humidity}}",
                    "unique_id": device.safe_name + "_h",
                },
                f"{device.safe_name.lower()}_battery1": {
                    "platform": "sensor",
                    "device_class": "battery",
                    "unit_of_measurement": "%",
                    "value_template": "{{ value_json.battery}}",
                    "unique_id": device.safe_name + "_b",
                },
            },
            "state_topic": get_topic_state(device),
        }

        mqtt_send_message(get_topic_discovery(device), message)

def mqtt_remove_discovery(device: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        mqtt_send_message(get_topic_discovery(device), "")


def mqtt_send_message(topic: str, message) -> None:
    if not config.MQTT_ENABLE:
        return

    message = json.dumps(message)
    publish.single(
                    topic,
                    message,
                    retain=True,
                    hostname=config.MQTT_HOST,
                    port=config.MQTT_PORT,
                    auth={'username':config.MQTT_USERNAME, 'password':config.MQTT_PASSWORD}
                )
    Log.msg(f"Sent to MQTT {topic}: {message}")


def mqtt_send_state(message, device: Device) -> None:
    if not config.MQTT_ENABLE:
        return

    mqtt_send_message(get_topic_state(device), message)

def mqtt_send_domoticz(domoticz_id, message) -> None:
    if not config.MQTT_ENABLE:
        return

    topic = "domoticz/in"
    message = {
        "command":"udevice", 
        "idx": domoticz_id, 
        "svalue": str(message['temperature']) + ";" + str(message['humidity']) + ";0"
    }
    mqtt_send_message(topic, message)

"""
General functions
"""
def toSigned16(bytes):
    return (((bytes[0] << 8) + bytes[1]) ^ 0x8000) - 0x8000

"""
Bleak
"""
def notification_handler(_: int, data: bytearray, device: Device):
    Log.msg("Received data", device.name)
    dataSize = len(data)
    
    # Check message header
    if ( (dataSize > 6) and  (data[0] != 170) or (data[1] != 170) ):
        msg = "Unknown data",', '.join('{:02x}'.format(x) for x in data)
        Log.msg(msg, level="ERROR")
        return
    
    # Check checksum
    payloadSize = (data[3] << 8) + data[4]
    checksum = sum(data[0:payloadSize+5]) % 256
    if checksum != data[dataSize-2]:
        msg = "Checksum error:", checksum, data[dataSize-2], "data",', '.join('{:02x}'.format(x) for x in data)
        Log.msg(msg, level="ERROR")
        return
        
    if ((data[2] == 162) and (dataSize > 10)):
        result = {
            "temperature": toSigned16(data[5:7]) / 10.0,
            "humidity": ((data[7] << 8) + data[8]) / 10.0,
            "battery": data[9] * 100,
            "unit": "Celsius" if data[10] == 0 else "Fahrenheit"
        }
        Log.msg(result)
        mqtt_send_state(result, device)
        if hasattr(device, "domoticz_idx") and device.domoticz_idx > 0:
            mqtt_send_domoticz(device.domoticz_idx, result)

    # Extra data
    if ((data[2] == 163)):
        msg = "Hour data", ', '.join('{:02x}'.format(x) for x in data)
        Log.msg(msg, level="DEBUG")
    
    if ((data[2] == 164)):
        msg = "Version Info", ''.join(chr(x) for x in data)
        Log.msg(msg, level="DEBUG")
    
    msg = "Other data", ', '.join('{:02x}'.format(x) for x in data)
    Log.msg(msg, level="DEBUG")

    return

async def deviceConnect(device: Device):
    while True:
        Log.msg(f'Scanning for device {device.name}')

        if not device.mac:
            Log.msg("Currently only by device address is supported", level="ERROR")
            return False

        try:
            ble_device = await BleakScanner.find_device_by_address(device.mac)
        except BleakDBusError as err:
            if err.dbus_error == 'org.bluez.Error.InProgress':
                Log.msg(f"Interface busy while trying to connect to {device.name}, retry in 5 seconds", level="WARNING")
            else:
                Log.msg(f"[ERROR]: BleakDBusError: {err}", level="ERROR")
            await asyncio.sleep(5)

            continue

        if ble_device is None:
            Log.msg(f"Could not find device with address {device.mac}", level="NOTICE")
            return False

        Log.msg("Device found, attempting connection", device.name)

        # Set device name to blu name
        device.name = ble_device.name

        disconnected_event = asyncio.Event()

        def disconnect_handler(client: BleakClient):
            Log.msg("Disconnected", device.name)
            mqtt_remove_discovery(device)
            client.disconnect()
            disconnected_event.set()

        try:
            async with BleakClient(ble_device, disconnected_callback=disconnect_handler) as client:
                Log.msg("Connection successful", device.name)
                mqtt_send_discovery(device)

                await client.start_notify(notify_uuid, partial(notification_handler, device=device))
                await asyncio.sleep(10)

                try:
                    await disconnected_event.wait()
                except asyncio.exceptions.CancelledError:
                    Log.msg("Cancelling connection, disconnecting", device.name)
                    await client.disconnect()
        except AssertionError:
            return False


    Log.msg("Too many errors, stopping", level="ERROR")
    

async def main(devicesCfg: list):
    lock = asyncio.Lock()
    await asyncio.gather(*(deviceConnect(device) for device in devicesCfg))
  
if __name__ == "__main__":
    # Instantiate device objects from config
    devices = []
    for device_cfg in config.DEVICES:
        devices.append(Device(device_cfg))

    try:
        asyncio.run(main(devices))
    except TimeoutError:
        Log.msg("Connection failure: timeout", level="ERROR")
    except OSError:
        Log.msg("Bluetooth interface not ready for use. Did you enable the if?", level="WARNING")
    except KeyboardInterrupt:
        Log.msg("Exit by user.")
