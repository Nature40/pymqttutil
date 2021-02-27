import argparse
import configparser
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

logger = logging.getLogger("mqttutil")


class Task:
    def __init__(self,
                 mqtt_c: mqtt.Client,
                 topic: str,
                 func: str,
                 scheduling_interval: str,
                 topic_prefix: str = platform.node(),
                 requires: List[str] = [],
                 **kwargs):
        super().__init__()

        for imp in requires:
            if imp not in globals():
                logger.info(f"importing module {imp}")
                globals()[imp] = __import__(imp)

        # text function
        self.func_str = func
        result = self._eval()

        # set mqtt
        self.mqtt_c = mqtt_c
        self.topic_prefix = topic_prefix
        self.topic_suffix = topic

        # test publish
        self._publish(self.topic, result)

        # add to schedule
        self.scheduling_interval_s = timeparse(scheduling_interval)
        schedule.every(self.scheduling_interval_s).seconds.do(Task.run, self)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.func_str}')"

    @property
    def topic(self):
        if not self.topic_prefix:
            return self.topic_suffix
        elif self.topic_prefix.endswith("/"):
            return self.topic_prefix + self.topic_suffix
        else:
            return self.topic_prefix + "/" + self.topic_suffix

    def _eval(self):
        result = eval(self.func_str)
        logger.debug(f"exec {self.func_str} = {result}")
        return result

    def _publish(self, topic: str, result):
        # don't publish Nones
        if result is None:
            return

        # publish primitive data directly
        elif type(result) in [int, float, str]:
            logger.info(f"publish {topic} {result}")
            self.mqtt_c.publish(topic, result)

        # expand dict by keys
        elif isinstance(result, dict):
            for k, v in result.items():
                self._publish(f"{topic}/{k}", v)

        # iterate list (via dict conversion)
        elif isinstance(result, list):
            self._publish(topic, dict(enumerate(result)))

        elif isinstance(result, tuple):
            # recurse as dict for namedtuple
            if hasattr(result, '_asdict') and hasattr(result, '_fields'):
                self._publish(topic, result._asdict())
            # iterate regular tuple (via dict conversion)
            else:
                self._publish(topic, dict(enumerate(result)))

        # print info on unknown result types
        else:
            logger.warning(f"type {type(result)} is not supported. ({topic})")

    def run(self):
        result = self._eval()
        self._publish(self.topic, result)


if __name__ == "__main__":
    args = parser.parse_args()

    # setup logger
    logger_level = max(0, logging.WARN - (args.verbose * 10))
    logging.basicConfig(level=logger_level)

    # get mqtt config
    mqtt_c = mqtt.Client()
    mqtt_c.connect(args.mqtt_host, args.mqtt_port)

    # parse config
    config = configparser.ConfigParser()
    config.read(args.config)

    # tasks
    tasks: List[Task] = []

    # look for known sections
    for topic in config.sections():
        vars = {k: literal_eval(v) for k, v in config.items(topic)}
        tasks.append(Task(mqtt_c, topic, **vars))

    if not tasks:
        logger.critical("No valid tasks specified, exiting.")
        exit(1)

    running = True
    while running:
        time.sleep(1)
        schedule.run_pending()
