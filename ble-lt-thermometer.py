import asyncio
from functools import partial
from typing import Optional
import json
import re

import bleak
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
    custom_name: Optional[str] = ""
    mac: str = ""
    wait: int = 30
    domoticz_idx: Optional[int] = 0

    def __init__(self, options: dict):
        for option, value in options.items():
            if not hasattr(self, option):
                continue

            setattr(self, option, value)

"""
MQTT functions
"""
def get_topic_state(client: BleakClient, deviceCfg: Device) -> str:
    return config.MQTT_PREFIX + client_get_name(client, deviceCfg) + "/state"

def get_topic_discovery(client: BleakClient, deviceCfg: Device) -> str:
    return config.MQTT_DISCOVERY_PREFIX + "sensor/" + client_get_name(client, deviceCfg) + "/config"

def mqtt_send_discovery(client: BleakClient, deviceCfg: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        name = client_get_name(client, deviceCfg)
        message =  {
            "device_class": "temperature", 
            "name": name ,
            "state_topic": get_topic_state(client, deviceCfg),
            "value_template": "{{ value_json.temperature}}",
            "json_attributes_topic": get_topic_state(client, deviceCfg),
            "unit_of_measurement": "°C", 
            "icon": "mdi:thermometer"
        }
        mqtt_send_message(get_topic_discovery(client, deviceCfg), message)

def mqtt_remove_discovery(client: BleakClient, deviceCfg: Device):
    if config.MQTT_DISCOVERY and config.MQTT_ENABLE:
        mqtt_send_message(get_topic_discovery(client, deviceCfg), "")


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


def mqtt_send_state(client: BleakClient, message, deviceCfg: Device) -> None:
    if not config.MQTT_ENABLE:
        return

    mqtt_send_message(get_topic_state(client, deviceCfg), message)

def mqtt_send_domoticz(client: bleak.BleakClient, domoticz_id, message) -> None:
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
def client_get_name(client: bleak.BleakClient, deviceCfg: Device) -> str:
    name = client.address
    if deviceCfg.custom_name:
        name = deviceCfg.custom_name
    elif client._device_info["Name"]:
        name = client._device_info["Name"]

    # Sanitize
    name = re.sub('[^a-zA-Z0-9_]', '', name)
    return name    

def toSigned16(bytes):
    return (((bytes[0] << 8) + bytes[1]) ^ 0x8000) - 0x8000

"""
Bleak
"""
def notification_handler(_: int, data: bytearray, client: BleakClient, deviceCfg: Device):
    print(f"[{deviceCfg.custom_name}] Received data")
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
            "unit": "Celsius" if data[10] == 0 else "Fahrenheit"
        }
        print(result)
        mqtt_send_state(client, result, deviceCfg)
        if hasattr(deviceCfg, "domoticz_idx") and deviceCfg.domoticz_idx > 0:
            mqtt_send_domoticz(client, deviceCfg.domoticz_idx, result)

        return
    
    if ((data[2] == 163)):
        print("Hour data", ', '.join('{:02x}'.format(x) for x in data))
        return
    
    if ((data[2] == 164)):
        print("Version Info", ''.join(chr(x) for x in data))
        return
    
    print("Other data", ', '.join('{:02x}'.format(x) for x in data))

    #client.disconnect()
    
async def deviceConnect(deviceCfg: Device):
    print(f'Scanning for device {deviceCfg.custom_name}')

    if not deviceCfg.mac:
        print("Currently only by device address is supported")
        return

    try:
        ble_device = await BleakScanner.find_device_by_address(deviceCfg.mac)
    except BleakDBusError as err:
        print(f"[ERROR]: BleakDBusError: {err}")
        return

    if ble_device is None:
        print(f"Could not find device with address {deviceCfg.mac}")
        return

    print(f"[{deviceCfg.custom_name}] Device found, attempting connection")

    disconnected_event = asyncio.Event()

    def disconnect_handler(client: BleakClient):
        print("Disconnected from", deviceCfg.custom_name)
        mqtt_remove_discovery(client, deviceCfg)
        client.disconnect()
        disconnected_event.set()

    try:
        async with BleakClient(ble_device, disconnected_callback=disconnect_handler) as client:
            print(f"[{deviceCfg.custom_name}] Connection successful")
            mqtt_send_discovery(client, deviceCfg)

            await client.start_notify(notify_uuid, partial(notification_handler, client=client, deviceCfg=deviceCfg))
            await asyncio.sleep(deviceCfg.wait)
            await client.stop_notify(notify_uuid)

            try:
                await disconnected_event.wait()
            except asyncio.exceptions.CancelledError:
                print(f"[{deviceCfg.custom_name}] Cancelling connection, disconnecting")
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
    except KeyboardInterrupt:
        print("Exit by user.")
