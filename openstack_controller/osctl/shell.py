#!/usr/bin/env python3
import argparse

from openstack_controller.osctl import plugins


class Osctl:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Client to manage OpenStackDeployment resource."
        )
        self.subparsers = self.parser.add_subparsers(
            dest="subcommand", required=True
        )
        self.plugins = self.load_plugins()
        self.args = self.parser.parse_args()

    def load_plugins(self):
        res = {}
        for name, plugin in plugins.registry.items():
            instance = plugin(self.parser, self.subparsers)
            instance.build_options()
            res[name] = instance
        return res

    def run(self):
        self.plugins[self.args.subcommand].run(self.args)
        pass


def main():
    osctl = Osctl()
    osctl.run()


if __name__ == "__main__":
    main()