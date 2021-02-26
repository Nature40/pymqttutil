# pymqttutil

Publish system information via MQTT.

## Usage

```
$ python3 -m mqttutil --help
usage: mqttutil [-h] [-c CONFIG] [-v] [--mqtt-host MQTT_HOST] [--mqtt-port MQTT_PORT] [--mqtt-prefix MQTT_PREFIX]

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
  --mqtt-prefix MQTT_PREFIX
                        mqtt prefix to use for publishing (default: $HOSTNAME)
```

## Configuration

mqttutil's configuration consists of two parts. The `[DEFAULT]` section is evaluated and used in all latter defined tasks.

```ini
[DEFAULT]
scheduling_interval = "5s"
```

The sections following the pattern `[psutil.*]` are interpreted functions in the [psutil module](https://psutil.readthedocs.io/en/latest/). The parameters are handed over as the function is called.

```ini
[psutil.cpu_percent]
interval = 0.1
percpu = False
```

An example configuration file is provided in [etc/mqttutil.conf](etc/mqttutil.conf)
