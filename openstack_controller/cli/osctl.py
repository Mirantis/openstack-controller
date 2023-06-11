#!/usr/bin/env python3

from openstack_controller.osctl import shell


def main():
    osctl = shell.Osctl()
    osctl.run()


if __name__ == "__main__":
    main()
