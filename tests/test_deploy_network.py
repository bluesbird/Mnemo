import ipaddress
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
    proxy = config["networks"]["proxy"]["ipam"]["config"][0]
    subnet = ipaddress.ip_network(proxy["subnet"])
    dynamic_range = ipaddress.ip_network(proxy["ip_range"])
    caddy = ipaddress.ip_address(
        config["services"]["caddy"]["networks"]["proxy"]["ipv4_address"]
    )

    assert dynamic_range.subnet_of(subnet)
    assert caddy in subnet
    assert caddy not in dynamic_range
    assert "ipv4_address" not in (
        config["services"]["ui"]["networks"]["proxy"] or {}
    )
    static_addresses = [
        service["networks"]["proxy"]["ipv4_address"]
        for service in config["services"].values()
        if (service.get("networks", {}).get("proxy") or {}).get("ipv4_address")
    ]
    assert len(static_addresses) == len(set(static_addresses))

    nginx = (ROOT / "ui" / "docker" / "default.conf.template").read_text()
    trusted_addresses = re.findall(r"^\s*set_real_ip_from\s+([^;]+);", nginx, re.M)
    assert trusted_addresses == [str(caddy)]


class DeploymentNetworkTests(unittest.TestCase):
    def test_proxy_dynamic_addresses_cannot_claim_caddy_address(self):
        assert_proxy_network()


if __name__ == "__main__":
    unittest.main()
