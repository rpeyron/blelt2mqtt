# Device Settings
# {
#   'mac'         : (required) MAC Address of the bluetooth LT Thermometer
#   'name'        : (optional) to override the name provided by bluetooth
#   'domoticz_idx': (optional) id of the virtual sensor to be updated through domoticz   
# }

DEVICES = [ 
   {'mac': "C8:33:DE:43:2C:00", 'name': "LT Bureau", 'domoticz_idx': 396},
   {'mac': "C8:33:DE:43:2C:01"},
]


# MQTT Settings

MQTT_HOST="127.0.0.1"                   # MQTT Server (defaults to 127.0.0.1)
MQTT_PORT=1883                          # Defaults to 1883
MQTT_USERNAME="username"                # Username for MQTT server ('username' if not required)
MQTT_PASSWORD=None                      # Password for MQTT (None if not required)
MQTT_PREFIX="lt_temp/"                  # MQTT Topic Prefix. 
MQTT_DISCOVERY=True                     # Home Assistant Discovery (true/false), defaults to true
MQTT_DISCOVERY_PREFIX="homeassistant/"  # Home Assistant Discovery Prefix, defaults to homeassistant/
