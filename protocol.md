## LT Thermometer Protocol

service_uuid: "0000FFE5-0000-1000-8000-00805f9b34fb"
notify_uuid: "0000FFE8-0000-1000-8000-00805f9b34fb"

### Common structure format

The notification you will get once subscribed to the notify_uuid above will have the following structure

|Bytes|Contents|
| :-: |-|
|0,1|Header 0xAAAA|
|2|Data Type :<br />- 0xA2 (162) : hygrometer<br />- 0xA3 (163) : hour data<br />- 0xA4 (164) : version info |
|3,4|Data size in bytes (as 'n' below)|
|5,n+4|Data according to data type (see below)|
|n+5|Checksum (sum of bytes 0 - n+4 modulo 256)|
|n+6|Footer 0x55|

Note: when two bytes are used, the big indian notation (most significant byte on the left)

### Hygrometer data types

The hygrometer data type is the one with the third byte value equal to 0xA2 (162), and have a data size of 6 bytes.

|Bytes|Contents|
| :-: |-|
|  | <i>See above for first 5 bytes structure</i>|
|5,6|Temperature (to be divided by 10)|
|7,8|Humidity (to be divided by 10)|
|9|Power indicator|
|10|Unit (0 for Celcius)|
|  | <i>See above for last 2 bytes structure</i>|


### Other data types

Version Info (0xA4): string

Hour Info (0xA3): it is an array of 4 bytes:  1 entry per hour, last entry for current time with  0,1 = temperature * 10 and   2,3 = humidity * 10
