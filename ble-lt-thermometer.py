import asyncio
from functools import partial
from typing import Optional
import json
import re

from bleak import BleakScanner, BleakClient
from bleak.exc import BleakDBusError
import paho.mqtt.publish as publish

import config

# Install requirements :
# pip3 install -r requirements.txt
#
# Edit config in config.py


# The UUID of LT Thermometer v3 & v4 protocol
service_uuid = "0000FFE5-0000-1000-8000-00805f9b34fb"
notify_uuid = "0000FFE8-0000-1000-8000-00805f9b34fb"
char_uuid = "00002902-0000-1000-8000-00805f9b34fb"

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

def get_topic_discovery(device: Device, suffix: str = "t") -> str:
    return config.MQTT_DISCOVERY_PREFIX + f"device/{device.safe_name}_{suffix}/config"

def mqtt_send_discovery(device: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        message = {
            "device": {
                "ids": device.safe_name,
                "name": device.name,
            },
            "origin": {
                "name": "blelt2mqtt",
                "sw_version": "0.1.0.0",
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

        mqtt_send_message(get_topic_discovery(device, "t"), message)
        mqtt_send_message(get_topic_discovery(device, "h"), message)
        mqtt_send_message(get_topic_discovery(device, "b"), message)

def mqtt_remove_discovery(device: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        mqtt_send_message(get_topic_discovery(device, "t"), "")
        mqtt_send_message(get_topic_discovery(device, "h"), "")
        mqtt_send_message(get_topic_discovery(device, "b"), "")


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
    print("Sent to MQTT", topic, ": ", message)


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
    print(f"[{device.name}] Received data")
    dataSize = len(data)
    
    # Check message header
    if ( (dataSize > 6) and  (data[0] != 170) or (data[1] != 170) ):
        print("Unknown data",', '.join('{:02x}'.format(x) for x in data))
        return
    
    # Check checksum
    payloadSize = (data[3] << 8) + data[4]
    checksum = sum(data[0:payloadSize+5]) % 256
    if checksum != data[dataSize-2]:
        print("Checksum error:", checksum, data[dataSize-2], "data",', '.join('{:02x}'.format(x) for x in data))
        return
        
    if ((data[2] == 162) and (dataSize > 10)):
        result = {
            "temperature": toSigned16(data[5:7]) / 10.0,
            "humidity": ((data[7] << 8) + data[8]) / 10.0,
            "power": data[9] * 100,
            "battery": data[9] * 100,
            "unit": "Celsius" if data[10] == 0 else "Fahrenheit"
        }
        print(result)
        mqtt_send_state(result, device)
        if hasattr(device, "domoticz_idx") and device.domoticz_idx > 0:
            mqtt_send_domoticz(device.domoticz_idx, result)

        return
    
    if ((data[2] == 163)):
        print("Hour data", ', '.join('{:02x}'.format(x) for x in data))
        return
    
    if ((data[2] == 164)):
        print("Version Info", ''.join(chr(x) for x in data))
        return
    
    print("Other data", ', '.join('{:02x}'.format(x) for x in data))

    #client.disconnect()
    
async def deviceConnect(device: Device):
    print(f'Scanning for device {device.name}')

    if not device.mac:
        print("Currently only by device address is supported")
        return

    try:
        ble_device = await BleakScanner.find_device_by_address(device.mac)
    except BleakDBusError as err:
        print(f"[ERROR]: BleakDBusError: {err}")
        return

    if ble_device is None:
        print(f"Could not find device with address {device.mac}")
        return

    print(f"[{device.name}] Device found, attempting connection")

    # Set device name to blu name
    device.name = ble_device.name

    disconnected_event = asyncio.Event()

    def disconnect_handler(client: BleakClient):
        print("Disconnected from", device.name)
        mqtt_remove_discovery(device)
        client.disconnect()
        disconnected_event.set()

    try:
        async with BleakClient(ble_device, disconnected_callback=disconnect_handler) as client:
            print(f"[{device.name}] Connection successful")
            mqtt_send_discovery(device)

            await client.start_notify(notify_uuid, partial(notification_handler, device=device))
            await asyncio.sleep(device.wait)
            await client.stop_notify(notify_uuid)

            try:
                await disconnected_event.wait()
            except asyncio.exceptions.CancelledError:
                print(f"[{device.name}] Cancelling connection, disconnecting")
                await client.disconnect()
    except AssertionError:
        return


    print("Too many errors, stopping")
    

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
        print("Connection failure: timeout")
    except OSError:
        print("Bluetooth interface not ready for use. Did you enable the if?")
    except KeyboardInterrupt:
        print("Exit by user.")
