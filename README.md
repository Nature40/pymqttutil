# pymqttutil

Publish system information via MQTT.

## Usage

```
$ python3 -m mqttutil --help
usage: mqttutil [-h] [-c CONFIG] [-v]

publish system information via mqtt

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        configuration file
  -v, --verbose         increase output verbosity
```

## Configuration

mqttutil's configuration consists of two parts. The `[DEFAULT]` and the `[mqtt]` sections are there for configuring mqttutil defaults and the mqtt connection options. 

```ini
[DEFAULT]
scheduling_interval = "5s"
mqtt_prefix = "curta"

[mqtt]
client_id = "mqttutil"
host = "localhost"
port = 1883
```

The sections following the pattern `[psutil.*]` are interpreted functions in the [psutil module](https://psutil.readthedocs.io/en/latest/). The parameters are handed over as the function is called.

```ini
[psutil.cpu_percent]
interval = 0.1
percpu = False
```

An example configuration file is provided in [etc/mqttutil.conf](etc/mqttutil.conf)
