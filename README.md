# blelt2mqtt : Bluetooth LE LT Thermometer 2 MQTT

This software is a simple gateway to publish on MQTT for use with [Home Assistant](https://www.home-assistant.io/) or [Domoticz](https://www.domoticz.com/) temperature data from cheap bluetooth sensor LT Thermometer


## Supported devices

| Device | Photo | Where to find (examples) |
| :-: |  :-: |  - | 
| LT Thermometer v3 | ![LT Thermometer](docs/ble_lt_thermometer.jpg) | [AliExpress](https://fr.aliexpress.com/item/1005004073828412.html) |

These devices are supported by an android application named "qaqa" which is available here : https://d.ihunuo.com/app/dqwu (LT-Thermometer v3.apk)


## Install

Prerequisites:
* Linux, Windows or MacOS (only tested on Linux / Raspberry)
* Bluetooth LE compatible device (with installed stack)
* Python3 with pip3

Installation steps:
1. Install needed Python modules (bleak, paho-mqtt)

```
pip3 install -r requirements.txt
```

2. Configure your sensor anq MQTT server in the configuration file

3. To ensure the software is launched at startup :

```
crontab -e

@reboot bash /path/to/blelt.sh
```

## Configure Domoticz / Home Assistant

This should not require extra configuration for use with MQTT auto-discovery.

If you want to have a domoticz sensor with temperature and humidity, you need to follow these steps:
1. Configure a virtual sensor Temperature+Humidity through the Dummy hardware in Hardware menu
2. Read the idx of the created device in the Devices menu
3. Add the idx in the configuration file as 'domoticz_idx'

You should now see the sensor (native sensor on the left, auto-discovered on the right) :
![Example of sensor in domoticz](./docs/domoticz.png)


## Protocol

The reverse-engineered protocol is described in [protocol.md](./protocol.md) and the process is described in this [article (in french)](https://www.lprp.fr/2022/07/capteur-bluetooth-le-temperature-dans-domoticz-par-reverse-engineering-et-mqtt-auto-discovery-domoticz-et-home-assistant/)


## Useful links

* [LT-Thermometer v3](https://d.ihunuo.com/app/dqwu) Android or iOS application
* Bluetooth UUID [Nordic open database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) and [official 16-bits list](https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf) <i>(spoiler: the used UUID aren't in there...)</i>
* [BLE Tutorial for Arduino](https://www.sgwireless.com/uploads/ueditor/upload/file/20200315/AN-101%20Enabling%20BLE%20function%20on%20Arduino%20Platform%20with%20SGW1010-EVK.pdf)
* Home Assistant [auto-discovery protocol](https://www.home-assistant.io/docs/mqtt/discovery/) and [fields definition for sensors](https://www.home-assistant.io/integrations/sensor.mqtt/)
* Domoticz auto-discovery support with [native client](https://www.domoticz.com/wiki/MQTT#Add_hardware_.22MQTT_Auto_Discovery_Client_Gateway.22) or [plugin](https://github.com/emontnemery/domoticz_mqtt_discovery)
* Domoticz MQTT [sensor messages format](https://piandmore.wordpress.com/2019/02/04/mqtt-out-for-domoticz/)


## License & Credits

GPL 

2022 - Remi Peyronnet