import json
import os
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def assert_proxy_network():
    environment = os.environ.copy()
    environment.update({
        name: "compose-validation-only"
        for name in (
            "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
            "RABBITMQ_USER", "RABBITMQ_PASSWORD", "MNEMO_RESET_API_KEY", "GROQ_API_KEY",
        )
    })
    result = subprocess.run(
        ["docker", "compose", "-f", str(ROOT / "deploy" / "compose.yaml"),
         "config", "--format", "json"],
        env=environment, check=True, capture_output=True, text=True,
    )
    config = json.loads(result.stdout)
    proxy = config["networks"]["proxy"]
    assert proxy["external"] is True
    assert proxy["name"] == "deploy_proxy"
    assert not proxy.get("ipam", {}).get("config")
    assert "caddy" not in config["services"]
    assert "proxy" in config["services"]["ui"]["networks"]
    assert "ipv4_address" not in (
        config["services"]["ui"]["networks"]["proxy"] or {}
    )
    for name, service in config["services"].items():
        assert not service.get("ports") or name == "ui"
    assert all(port["host_ip"] == "127.0.0.1"
               for port in config["services"]["ui"]["ports"])
    assert "caddy_data" not in config["volumes"]
    assert "caddy_config" not in config["volumes"]

    nginx = (ROOT / "ui" / "docker" / "default.conf.template").read_text()
    trusted_addresses = re.findall(r"^\s*set_real_ip_from\s+([^;]+);", nginx, re.M)
    assert trusted_addresses == ["172.30.0.2"]


class DeploymentNetworkTests(unittest.TestCase):
    def test_gateway_is_external_and_only_ui_is_exposed(self):
        assert_proxy_network()


if __name__ == "__main__":
    unittest.main()
