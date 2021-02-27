# pymqttutil

Publish system information via MQTT.

## Usage

```
$ python3 -m mqttutil --help
usage: mqttutil [-h] [-c CONFIG] [-v] [--mqtt-host MQTT_HOST] [--mqtt-port MQTT_PORT]

publish system information via mqtt

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        configuration file (default: etc/mqttutil.conf)
  -v, --verbose         increase output verbosity (default: 0)

mqtt:
  --mqtt-host MQTT_HOST
                        hostname of mqtt broker (default: localhost)
  --mqtt-port MQTT_PORT
                        port of mqtt broker (default: 1883)

```

## Configuration

mqttutil's configuration consists of tasks defined in individual sections, e.g.:

```ini
[announce]
func = "platform.node()"
scheduling_interval = "1s"
topic_prefix = ""
requires = ["platform"]
```

In the example above the python statement `platform.node()` is evaluated once per second and published to the `announce` topic. The parameters `topic_prefix` as well as `requires` are optional. `topic_prefix` defaults to the hostname, if not defined. 

The parameter `requires` can be used to import additonal modules, such as the [psutil module](https://psutil.readthedocs.io/en/latest/). 

```ini
[load]
func = "psutil.getloadavg()"
scheduling_interval = "5s"
```

### DEFAULT section 

The `DEFAULT` section allows to initialize the parameters for all sections. Note that the `topic_prefix` option is initialized globally by the hostname, and is not required to be set.

```ini
[DEFAULT]
scheduling_interval = "5s"

[announce]
func = "platform.node()"
topic_prefix = ""

[unixtime]
func = "time.time()"
requires = ["time"]
```

A comprehensive example configuration file is provided at [etc/mqttutil.conf](etc/mqttutil.conf).
