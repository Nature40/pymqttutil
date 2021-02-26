import argparse
import configparser
import json
import logging
import platform
import time
from ast import literal_eval
from typing import List

import paho.mqtt.client as mqtt
import schedule
from pytimeparse.timeparse import timeparse

parser = argparse.ArgumentParser("mqttutil",
                                 description="publish system information via mqtt",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                 )
parser.add_argument("-c", "--config", help="configuration file", type=str, default="etc/mqttutil.conf")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="count", default=0)

publish_options = parser.add_argument_group("mqtt")
publish_options.add_argument("--mqtt-host", help="hostname of mqtt broker", default="localhost", type=str)
publish_options.add_argument("--mqtt-port", help="port of mqtt broker", default=1883, type=int)
publish_options.add_argument("--mqtt-prefix", help="mqtt prefix to use for publishing", default=platform.node(), type=str)


class Task:
    def __init__(self, func_str: str, mqtt_c: mqtt.Client, mqtt_prefix: str, scheduling_interval: str, **kwargs):
        super().__init__()

        # text function
        self.func_str = func_str
        result = self._eval()

        # set mqtt
        self.mqtt_c = mqtt_c
        self.mqtt_prefix = mqtt_prefix
        self.mqtt_suffix = func_str.replace(".", "/")

        # test publish
        processed = self._process(result)
        self._publish(processed)

        # add to schedule
        self.scheduling_interval_s = timeparse(scheduling_interval)
        schedule.every(self.scheduling_interval_s).seconds.do(Task.run, self)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.func_str}')"

    @property
    def mqtt_topic(self):
        if not self.mqtt_prefix:
            return self.mqtt_suffix
        elif self.mqtt_prefix.endswith("/"):
            return self.mqtt_prefix + self.mqtt_suffix
        else:
            return self.mqtt_prefix + "/" + self.mqtt_suffix

    def _eval(self):
        result = eval(self.func_str)
        logging.debug(f"exec {self.func_str} = {result}")
        return result

    @staticmethod
    def _process(result):
        # return primitive types directly
        if result is None:
            return result
        elif type(result) in [int, float, str]:
            return result

        # return members of list, dict, tuple processed recursively
        elif isinstance(result, list):
            return [Task._process(item) for item in result]

        elif isinstance(result, dict):
            return {k: Task._process(v) for k, v in result.items()}

        elif isinstance(result, tuple):
            # if _asdict and _field is present -> namedtuple
            if hasattr(result, '_asdict') and hasattr(result, '_fields'):
                return Task._process(result._asdict())
            else:
                return Task._process(list(result))
        # if type is not handled explicitly, return result
        else:
            return result

    def _publish(self, processed):
        try:
            marshalled = json.dumps(processed)
            logging.info(f"publish {marshalled} -> {self.mqtt_topic}")
            self.mqtt_c.publish(self.mqtt_topic, marshalled)
        except TypeError as e:
            logging.warning(f"{self.func_str} failed: {repr(e)}")

    def run(self):
        result = self._eval()
        processed = self._process(result)
        self._publish(processed)


if __name__ == "__main__":
    args = parser.parse_args()

    # setup logging
    logging_level = max(0, logging.WARN - (args.verbose * 10))
    logging.basicConfig(level=logging_level)

    # get mqtt config
    mqtt_c = mqtt.Client()
    mqtt_c.connect(args.mqtt_host, args.mqtt_port)

    # parse config
    config = configparser.ConfigParser()
    config.read(args.config)

    # import requested modules
    imports = literal_eval(config["DEFAULT"]["imports"])
    for imp in imports:
        logging.info(f"importing module {imp}")
        globals()[imp] = __import__(imp)

    # tasks
    tasks: List[Task] = []

    # look for known sections
    for sec in config.sections():
        vars = {k: literal_eval(v) for k, v in config.items(sec)}

        # create and append task object
        try:
            task = Task(sec, mqtt_c, args.mqtt_prefix, **vars)
            tasks.append(task)
        except Exception as e:
            logging.critical(f"{sec}: {repr(e)}, exiting.")
            exit(1)

    if not tasks:
        logging.critical("No valid tasks specified, exiting.")
        exit(1)

    running = True
    while running:
        time.sleep(1)
        schedule.run_pending()
