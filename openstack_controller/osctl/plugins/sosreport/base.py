#!/usr/bin/env python3
import abc
import os


class BaseLogsCollector:
    name = ""
    registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls.name] = cls

    def __init__(self, args):
        self.args = args
        self.workspace = os.path.join(args.workspace, self.name)

    @abc.abstractmethod
    def get_tasks(self):
        """Returns tuple with task and arguments for logs collection."""
        pass
