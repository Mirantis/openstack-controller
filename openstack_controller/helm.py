import asyncio
import contextlib
import os
import re
import yaml
import tempfile
import threading
from asyncio.subprocess import PIPE

import kopf

from openstack_controller import utils
from openstack_controller import exception
from openstack_controller import kube

LOG = utils.get_logger(__name__)

HELM_LOCK = threading.Lock()


@contextlib.asynccontextmanager
async def helm_lock(lock):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lock.acquire)
    try:
        yield  # the lock is held
    finally:
        lock.release()


class HelmManager:
    def __init__(self, binary="helm3", namespace="openstack", history_max=1):
        self.binary = binary
        self.namespace = namespace
        self.max_history = str(history_max)
        self.env = dict(os.environ).update(
            {
                "HELM_NAMESPACE": namespace,
                "HELM_MAX_HISTORY": str(history_max),
            }
        )

    def _substitute_local_proxy(self, repo):
        node_ip = os.environ["NODE_IP"]
        return utils.substitute_local_proxy_hostname(repo, node_ip)

    async def _guess_and_delete(self, stderr):
        immutable_pattern = (
            r'Error: .*: cannot patch "(.*)" with kind ([a-zA-Z]+): '
        )
        m = re.match(immutable_pattern, stderr)
        if m:
            try:
                name, kind = m.group(1, 2)
            except:
                kopf.TemporaryError("Failed to guess name and kind.")
            LOG.info(f"Trying to remove kind: {kind} with name: {name}")
            kube_class = kube.get_object_by_kind(kind)
            if not kube_class:
                kopf.TemporaryError(
                    "Failed to find pykube class for kind: {kind}"
                )

            obj = kube.find(kube_class, name, self.namespace)
            if obj.exists():
                obj.delete()
                await kube.wait_for_deleted(obj)
            LOG.info(f"Successfully removed kind: {kind} with name {name}")

    async def run_cmd(self, cmd, raise_on_error=True):
        cmd = " ".join([self.binary, *cmd])
        LOG.info(
            "Running helm command started: '%s'",
            cmd,
        )
        process = await asyncio.create_subprocess_shell(
            cmd, env=self.env, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        async with helm_lock(HELM_LOCK):
            stdout, stderr = await process.communicate()
            stdout = stdout.decode() or None
            stderr = stderr.decode() or None

            LOG.debug(
                "Helm command output is: stdout: %s, stderr: %s",
                stdout,
                stderr,
            )
            if process.returncode and raise_on_error:
                LOG.error(
                    "Helm command failed. stdout: %s, stderr: %s",
                    stdout,
                    stderr,
                )
                if "field is immutable" in stderr:
                    LOG.warning("Trying to modify immutable object")
                    await self._guess_and_delete(stderr)
                    raise exception.HelmImmutableFieldChange()
                raise kopf.TemporaryError("Helm command failed")
            return (stdout, stderr)

    async def exist(self, name, args=None):
        args = args or []
        cmd = [
            "list",
            "--namespace",
            self.namespace,
            "-o",
            "json",
            *args,
        ]
        stdout, stderr = await self.run_cmd(cmd)
        for release in yaml.load(stdout):
            if release["name"] == name:
                return True

    async def list(self, args=None):
        args = args or []
        cmd = [
            "list",
            "--namespace",
            self.namespace,
            "-o",
            "json",
            *args,
        ]
        stdout, stderr = await self.run_cmd(cmd)
        return yaml.load(stdout)

    async def get_release_values(self, name, args=None):
        args = args or []
        cmd = [
            "get",
            "values",
            "--namespace",
            self.namespace,
            name,
            "-o",
            "json",
            *args,
        ]
        stdout, stderr = await self.run_cmd(cmd)
        return yaml.load(stdout)

    async def set_release_values(
        self, name, values, repo, chart, version, args=None
    ):
        args = args or []
        repo = self._substitute_local_proxy(repo)
        with tempfile.NamedTemporaryFile(
            mode="w", prefix=name, delete=True
        ) as tmp:
            yaml.dump(values, tmp)
            cmd = [
                "upgrade",
                name,
                "--repo",
                repo,
                chart,
                "--version",
                version,
                "--namespace",
                self.namespace,
                "--values",
                tmp.name,
                "--history-max",
                self.max_history,
                "--reuse-values",
                *args,
            ]
            await self.run_cmd(cmd)

    async def install(self, name, values, repo, chart, version, args=None):
        args = args or []
        repo = self._substitute_local_proxy(repo)
        with tempfile.NamedTemporaryFile(
            mode="w", prefix=name, delete=True
        ) as tmp:
            yaml.dump(values, tmp)
            cmd = [
                "upgrade",
                name,
                "--repo",
                repo,
                chart,
                "--namespace",
                self.namespace,
                "--version",
                version,
                "--values",
                tmp.name,
                "--history-max",
                self.max_history,
                "--install",
                *args,
            ]
            stdout, stderr = await self.run_cmd(cmd)

    async def install_bundle(self, data):
        repos = {r["name"]: r["url"] for r in data["spec"]["repositories"]}
        for release in data["spec"]["releases"]:
            repo, chart = release["chart"].split("/")
            repo = self._substitute_local_proxy(repo)
            await self.install(
                release["name"],
                release["values"],
                repos[repo],
                chart,
                release["version"],
            )

    async def delete(self, name, args=None):
        args = args or []
        cmd = ["delete", name, "--namespace", self.namespace, *args]

        stdout, stderr = await self.run_cmd(cmd, raise_on_error=False)
        if stderr and "Release not loaded" not in stdout:
            raise kopf.TemporaryError("Helm command failed")

    async def delete_bundle(self, data):
        for release in data["spec"]["releases"]:
            await self.delete(release["name"])
