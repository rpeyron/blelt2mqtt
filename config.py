# Device Settings
# {
#   'mac'         : (required) MAC Address of the bluetooth LT Thermometer
#   'custom_name' : (optional) to override the name provided by bluetooth
#   'domoticz_idx': (optional) id of the virtual sensor to be updated through domoticz
# }

DEVICES = [
   {'mac': "C8:33:DE:43:2C:00", 'custom_name': "LT Bureau", 'domoticz_idx': 96},
   {'mac': "C8:33:DE:43:2C:01", 'custom_name': "LT Bureau (14)", 'domoticz_idx': 39},
]

# Logging
# LOG_LEVEL Information to log  ERROR|WARNING|NOTICE|INFO|DEBUG    Defaults to INFO
LOG_LEVEL="INFO"

# MQTT Settings
MQTT_ENABLE=True                        # Enable MQTT. Publish MQTT messages or just print output. Default: True
MQTT_HOST="127.0.0.1"                   # MQTT Server (defaults to 127.0.0.1)
MQTT_PORT=1883                          # Defaults to 1883
MQTT_USERNAME="username"                # Username for MQTT server ('username' if not required)
MQTT_PASSWORD=None                      # Password for MQTT (None if not required)
MQTT_PREFIX="lt_temp/"                  # MQTT Topic Prefix. 
MQTT_DISCOVERY=True                     # Home Assistant Discovery (true/false), defaults to true
MQTT_DISCOVERY_PREFIX="homeassistant/"  # Home Assistant Discovery Prefix, defaults to homeassistant/
