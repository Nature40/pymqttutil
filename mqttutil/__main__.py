import argparse
import configparser
import inspect
import json
import logging
import platform
import time
from ast import literal_eval
from typing import Callable

import paho.mqtt.client as mqtt
import psutil
import schedule
from pytimeparse.timeparse import timeparse

parser = argparse.ArgumentParser("mqttutil", description="publish system information via mqtt")
parser.add_argument("-c", "--config", help="configuration file", type=str, default="etc/mqttutil.conf")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="count", default=0)


class Task:
    def __init__(self, func: Callable, func_path: str, scheduling_interval: str, mqtt_c: mqtt.Client, mqtt_prefix: str = platform.node(), **kwargs):
        super().__init__()

        # text function
        self.func = func
        self.func_path = func_path
        self.kwargs = kwargs
        self.exec()

        # set mqtt
        self.mqtt_c = mqtt_c
        self.mqtt_prefix = mqtt_prefix
        self.mqtt_suffix = func_path.replace(".", "/")

        # test publish
        self.publish()

        # add to schedule
        self.scheduling_interval_s = timeparse(scheduling_interval)
        schedule.every(self.scheduling_interval_s).seconds.do(Task.publish, self)

    def __repr__(self):
        return self.func.__repr__()

    @property
    def mqtt_topic(self):
        if not self.mqtt_prefix:
            return self.mqtt_suffix
        elif self.mqtt_prefix.endswith("/"):
            return self.mqtt_prefix + self.mqtt_suffix
        else:
            return self.mqtt_prefix + "/" + self.mqtt_suffix

    def exec(self):
        result = self.func(**self.kwargs)
        logging.debug(f"exec {self.func_path}({', '.join([k+'='+repr(v) for k,v in self.kwargs.items()])}) = {result}")
        return result

    def publish(self):
        try:
            result = self.exec()
            logging.info(f"publish {result} -> {self.mqtt_topic}")
            self.mqtt_c.publish(self.mqtt_topic, result)
        except TypeError as e:
            logging.warn(f"{self.func_path} failed: {repr(e)}")


class PsutilTask(Task):
    PREFIX = "psutil."

    def __init__(self, func_path: str, **kwargs):
        if not func_path.startswith(PsutilTask.PREFIX):
            raise ValueError(f"Function '{func_path}' is not supported.")

        # lookup function name in psutil module
        _, func_name = func_path.split(".")
        func = psutil.__dict__[func_name]

        super().__init__(func, func_path=func_path, **kwargs)

    def exec(self):
        psutil._common.scpufreq
        result = super().exec()

        if type(result) in [int, float, str, list, dict]:
            return json.dumps(result)
        elif isinstance(result, tuple):
            # is _asdict and _field is present -> namedtuple
            if hasattr(result, '_asdict') and hasattr(result, '_fields'):
                return json.dumps(result._asdict())
            else:
                return json.dumps(result)
        else:
            raise TypeError(f"{type(result)} is not supported")


if __name__ == "__main__":
    args = parser.parse_args()

    # setup logging
    logging_level = max(0, logging.WARN - (args.verbose * 10))
    logging.basicConfig(level=logging_level)

    # parse config
    config = configparser.ConfigParser()
    config.read(args.config)

    # tasks
    tasks = []

    # get mqtt config
    mqtt_args = dict(config.items("mqtt"))

    # paho mqtt does not ignore unused arguments, hence the non-matching need to be ignored
    init_args = {k: literal_eval(v)
                 for k, v in mqtt_args.items()
                 if k in inspect.signature(mqtt.Client.__init__).parameters}
    mqtt_c = mqtt.Client(**init_args)

    connect_args = {k: literal_eval(v)
                    for k, v in mqtt_args.items()
                    if k in inspect.signature(mqtt_c.connect).parameters}
    mqtt_c.connect(**connect_args)

    # look for known sectionss
    for sec in config.sections():
        vars = {k: literal_eval(v) for k, v in config.items(sec)}

        if sec.startswith("psutil."):
            try:
                task = PsutilTask(sec, mqtt_c=mqtt_c, **vars)
                tasks.append(task)
            except TypeError as e:
                logging.warning(f"skipping {sec}: {repr(e)}")

    running = True
    while running:
        time.sleep(1)
        schedule.run_pending()
