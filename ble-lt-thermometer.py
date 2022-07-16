import asyncio
from functools import partial
import bleak
import paho.mqtt.publish as publish
import json
import re

import config

# Install requirements :
# pip3 install bleak paho-mqtt
#
# Edit config in config.py


# The UUID of LT Thermometer v3 protocol
service_uuid = "0000FFE5-0000-1000-8000-00805f9b34fb"
notify_uuid = "0000FFE8-0000-1000-8000-00805f9b34fb"
char_uuid = "00002902-0000-1000-8000-00805f9b34fb"


def get_topic_state(client: bleak.BleakClient) -> str:
    return config.MQTT_PREFIX + client_get_name(client) + "/state"

def get_topic_discovery(client: bleak.BleakClient) -> str:
    return config.MQTT_DISCOVERY_PREFIX + "sensor/" + client_get_name(client) + "/config"

def mqtt_send_discovery(client: bleak.BleakClient):
    if config.MQTT_DISCOVERY:
        name = client_get_name(client)
        message =  {
            "device_class": "temperature", 
            "name": name , 
            "state_topic": get_topic_state(client),
            "value_template": "{{ value_json.temperature}}",
            "json_attributes_topic": get_topic_state(client),
            "unit_of_measurement": "°C", 
            "icon": "mdi:thermometer"
        }
        mqtt_send_message(get_topic_discovery(client), message)

def mqtt_remove_discovery(client: bleak.BleakClient):
    if config.MQTT_DISCOVERY:
        mqtt_send_message(get_topic_discovery(client), "")


def mqtt_send_message(topic: str, message) -> None:
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


def mqtt_send_state(client: bleak.BleakClient, message) -> None:
    mqtt_send_message(get_topic_state(client), message)

def mqtt_send_domoticz(client: bleak.BleakClient, domoticz_id, message) -> None:
    topic = "domoticz/in"
    message = {
        "command":"udevice", 
        "idx": domoticz_id, 
        "svalue": str(message['temperature']) + ";" + str(message['humidity']) + ";0"
    }
    mqtt_send_message(topic, message)


def client_get_name(client: bleak.BleakClient) -> str:
    try:
        if 'name' in client.ltDefinition:
            name = client.ltDefinition['name']
        else:
            name=client._device_info["Name"]
    except:
        name=client.address
    # Sanitize
    name = re.sub('[^a-zA-Z0-9_]', '', name)
    return name    


def notification_handler(client: bleak.BleakClient, sender, data):
    #print("notification_handler", sender, data)
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
            "temperature": ((data[5] << 8) + data[6]) / 10.0,
            "humidity": ((data[7] << 8) + data[8]) / 10.0,
            "power": data[9],
            "unit": "Celcius" if data[10] == 0 else "Farenheit"
        }
        print(result)
        mqtt_send_state(client, result)
        if 'domoticz_idx' in client.ltDefinition:
            mqtt_send_domoticz(client, client.ltDefinition['domoticz_idx'], result)
        return
    
    if ((data[2] == 163)):
        print("Hour data", ', '.join('{:02x}'.format(x) for x in data))
        return
    
    if ((data[2] == 164)):
        print("Version Info", ''.join(chr(x) for x in data))
        return
    
    print("Other data", ', '.join('{:02x}'.format(x) for x in data))
    

def disconnect_handler(client: bleak.BleakClient):
    print("Disconnected from", client_get_name(client))
    mqtt_remove_discovery(client)


async def deviceConnect(deviceDefinition):
    maxRetries = -1
    retry = 0
    while retry != maxRetries:
        try:
            c = bleak.BleakClient(deviceDefinition['mac'])
            c.ltDefinition = deviceDefinition
            await c.connect()
            if c.is_connected:
                retry = 0
                print("Connected to ", c._device_info["Name"])
                mqtt_send_discovery(c)
                
                c.set_disconnected_callback(disconnect_handler)
                
                await c.start_notify(notify_uuid, partial(notification_handler, c))
                
                while c.is_connected:
                    await asyncio.sleep(0.1)
                    
            else:
                print("Cannot connect")
        except bleak.exc.BleakError as err:
            retry+=1
            print("Error connecting : ", err)
            await asyncio.sleep(5.0)
        finally:
            await c.disconnect()

    print("Too much error, stopping")
    

async def main():
    await asyncio.gather(*[deviceConnect(definition) for definition in config.DEVICES])
  

asyncio.run(main())
