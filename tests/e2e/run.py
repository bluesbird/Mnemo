"""Cross-platform entry point: isolated project, bounded commands, diagnostics, teardown."""

import os
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent


def main():
    project = "mnemo-e2e-" + uuid.uuid4().hex[:12]
    env = {key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")}
    command = ["docker", "compose", "--project-name", project,
               "--env-file", str(HERE / "e2e.env"), "--file", str(HERE / "compose.yaml")]
    artifacts = HERE / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "project.txt").write_text(project, encoding="utf-8")
    scenario_log = artifacts / "scenario.log"
    scenario_log.write_text("Scenario not started.\n", encoding="utf-8")
    print(f"E2E project: {project}", flush=True)
    status = 1
    try:
        subprocess.run(["docker", "info"], env=env, check=True,
                       stdout=subprocess.DEVNULL, timeout=30)
        subprocess.run(command + ["up", "--detach", "--build"], env=env,
                       check=True, timeout=900)
        with scenario_log.open("w", encoding="utf-8") as log:
            subprocess.run(command + ["run", "--rm", "-T", "tests"], env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=420)
        status = 0
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"E2E failed: {exc}", file=sys.stderr)
    finally:
        print(scenario_log.read_text(encoding="utf-8", errors="replace"), flush=True)
        for name, args in (("status", ["ps", "--all"]),
                           ("logs", ["logs", "--no-color", "--timestamps", "--tail", "250"]),
                           ("queues", ["exec", "-T", "rabbitmq", "rabbitmqctl", "list_queues",
                                       "name", "messages_ready", "messages_unacknowledged", "consumers"])):
            try:
                result = subprocess.run(command + args, env=env, capture_output=True,
                                        text=True, errors="replace", timeout=30)
                output = result.stdout + result.stderr
                (artifacts / (name + ".log")).write_text(output, encoding="utf-8")
                if status:
                    print(output, file=sys.stderr)
            except (subprocess.SubprocessError, OSError) as exc:
                print(f"Could not collect {name}: {exc}", file=sys.stderr)
        try:
            subprocess.run(command + ["down", "--volumes", "--remove-orphans", "--rmi", "local",
                                      "--timeout", "10"],
                           env=env, check=True, timeout=90)
        except (subprocess.SubprocessError, OSError) as exc:
            print(f"Cleanup failed for {project}: {exc}", file=sys.stderr)
            status = 1
        print(f"E2E project: {project}; diagnostics: {artifacts}")
    return status


if __name__ == "__main__":
    sys.exit(main())
