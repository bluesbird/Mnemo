"""Cross-platform entry point: isolated project, bounded commands, diagnostics, teardown."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent


def verify_ms1_json_logs(output):
    records = []
    for line in output.splitlines():
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Invalid MS1 JSON log: {line}") from exc
        for field in ("@timestamp", "message"):
            assert isinstance(record.get(field), str) and record[field], (field, record)
        log = record.get("log")
        assert isinstance(log, dict), record
        for field in ("level", "logger"):
            assert isinstance(log.get(field), str) and log[field], (field, record)
        service = record.get("service")
        assert isinstance(service, dict), record
        assert service.get("name") == "ms1-knowledge-service", record
        records.append(record)
    assert any("Started KnowledgeServiceApplication" in record["message"]
               for record in records), "Missing MS1 structured startup log"


def verify_ms1_migrations(command, env):
    deadline = time.monotonic() + 120
    last_observation = "migration history not queried"
    while time.monotonic() < deadline:
        result = subprocess.run(
            command + ["exec", "-T", "db", "psql", "-U", "e2e", "-d", "mnemo_e2e",
                       "-At", "-c",
                       "SELECT count(*) || ':' || COALESCE(bool_and(success), false)::text "
                       "FROM flyway_schema_history WHERE version IN ('1', '2', '3') AND type = 'SQL'"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        last_observation = result.stdout.strip() or result.stderr.strip()
        if result.returncode == 0 and result.stdout.strip() == "3:true":
            break
        if result.returncode == 0 and result.stdout.strip() not in ("0:false", "1:true", "2:true", ""):
            raise AssertionError(
                "Expected successful fresh Flyway V1/V2/V3 migrations: " + last_observation)
        time.sleep(1)
    else:
        raise AssertionError("Timed out waiting for Flyway V1/V2/V3; last observation: "
                             + last_observation)
    subprocess.run(command + ["restart", "ms1"], env=env, check=True, timeout=60)
    print("PASS: fresh Flyway V1/V2/V3 applied and MS1 restarted with validated schema", flush=True)


def verify_ui_configuration(command, env):
    for service in ("ui", "ui-probe"):
        subprocess.run(command + ["exec", "-T", service, "nginx", "-t"],
                       env=env, check=True, timeout=30)
    for setting in (
        "UI_MS1_UPSTREAM=http://ms1:8080;include /etc/passwd",
        "UI_MS1_UPSTREAM=http://ms1:8080/api",
        "UI_MS2_UPSTREAM=http://ms2:8000\nhttp://ms2:8000",
        "UI_RATE_LIMITS=enabled",
    ):
        result = subprocess.run(
            command + ["run", "--rm", "--no-deps", "-T", "-e", setting, "ui", "true"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0 and "Invalid " in result.stderr, (
            "UI must reject unsafe runtime configuration", result.returncode, result.stderr)
    print("PASS: nginx configuration and runtime injection rejection", flush=True)


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
        verify_ms1_migrations(command, env)
        verify_ui_configuration(command, env)
        with scenario_log.open("w", encoding="utf-8") as log:
            subprocess.run(command + ["run", "--rm", "-T", "tests"], env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=420)
        from recovery import run as verify_recovery
        verify_recovery(command, env)
        logs = subprocess.run(command + ["logs", "--no-color", "--no-log-prefix", "ms1"],
                              env=env, capture_output=True, text=True, errors="replace",
                              check=True, timeout=30)
        (artifacts / "ms1-json.log").write_text(logs.stdout, encoding="utf-8")
        verify_ms1_json_logs(logs.stdout)
        print("PASS: MS1 ECS JSON logs include timestamp, level, logger, message and service",
              flush=True)
        status = 0
    except (subprocess.SubprocessError, OSError, AssertionError) as exc:
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
