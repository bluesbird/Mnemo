"""Preserve existing Docker storage and RabbitMQ identities across the service rename."""

import argparse
import json
import os
from pathlib import Path
import subprocess


def migrate(compose_file, env_file):
    command = ["docker", "compose", "-f", str(compose_file)]
    if env_file.exists():
        command += ["--env-file", str(env_file)]
    config = json.loads(subprocess.check_output(
        command + ["config", "--format", "json"], text=True))
    project = config["name"]
    containers = subprocess.check_output([
        "docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}",
        "--filter", "label=com.docker.compose.service=ms2-rag-service",
    ], text=True).split()
    if not containers:
        print("No legacy RAG container found; service-name migration not needed.")
        return
    if len(containers) != 1:
        raise RuntimeError("Expected one legacy RAG container; inspect the Compose project before migrating.")
    container = json.loads(subprocess.check_output(["docker", "inspect", containers[0]], text=True))[0]
    mounts = {mount["Destination"]: mount for mount in container["Mounts"]}
    overrides = {}
    for destination, setting in (("/app/data", "RAG_DATA_VOLUME"), ("/app/.cache", "RAG_CACHE_VOLUME")):
        mount = mounts.get(destination)
        if mount is None or mount["Type"] != "volume":
            raise RuntimeError(f"Expected a named volume at {destination}; refusing automatic migration.")
        overrides[setting] = mount["Name"]
    environment = dict(value.split("=", 1) for value in container["Config"]["Env"] if "=" in value)
    overrides["RAG_EVENTS_QUEUE"] = environment.get("MS2_EVENTS_QUEUE", "ms2.note-events")
    overrides["RAG_EVENTS_DEAD_LETTER_QUEUE"] = environment.get(
        "MS2_EVENTS_DEAD_LETTER_QUEUE", "ms2.note-events.dlq")
    text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    existing = dict(line.split("=", 1) for line in text.splitlines()
                    if "=" in line and not line.lstrip().startswith("#"))
    additions = []
    for key, value in overrides.items():
        if key in existing and existing[key].strip().strip("'\"") != value:
            raise RuntimeError(f"{key} conflicts with existing container state; resolve before deploying.")
        if key not in existing:
            additions.append(f"{key}={value}")
    if additions:
        # Append only non-secret identity overrides; never rewrite deployment credentials.
        descriptor = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as output:
            output.write("\n# Preserve storage and queued events during service rename\n"
                         + "\n".join(additions) + "\n")
    print("Service-name migration prepared: existing volumes and queues preserved in environment overrides.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", type=Path, default=Path("deploy/compose.yaml"))
    parser.add_argument("--env-file", type=Path, default=Path("deploy/.env"))
    arguments = parser.parse_args()
    migrate(arguments.compose, arguments.env_file)
