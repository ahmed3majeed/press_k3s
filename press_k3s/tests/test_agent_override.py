from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock


def _install_fake_frappe():
    """press_k3s.overrides.agent only touches frappe.db and frappe.flags."""
    fake = types.ModuleType("frappe")
    fake.db = MagicMock()
    fake.flags = types.SimpleNamespace(in_test=True)
    sys.modules["frappe"] = fake
    return fake


def _reset_press_k3s_modules():
    for mod in ("press_k3s.overrides.agent", "press_k3s.overrides", "press_k3s"):
        sys.modules.pop(mod, None)


class FakeAgent:
    """Minimal stand-in for press.agent.Agent covering the attrs _get_request_url reads."""

    def __init__(self, server_type, server, port, alt_port_servers=None):
        self.server_type = server_type
        self.server = server
        self.port = port
        if alt_port_servers is not None:
            self._Agent__servers_using_alt_ports = alt_port_servers


class PatchedGetRequestUrlTests(unittest.TestCase):
    def setUp(self):
        self.frappe = _install_fake_frappe()
        _reset_press_k3s_modules()
        from press_k3s.overrides.agent import patched_get_request_url

        self.patched_get_request_url = patched_get_request_url

    def test_k3s_enabled_uses_flask_origin_without_agent_prefix(self):
        agent = FakeAgent("Server", "s1.example.com", 443)
        self.frappe.db.get_value.side_effect = [
            True,  # custom_k3s_enabled
            "http://10.0.0.5:25052/",  # custom_k3s_agent_url, trailing slash on purpose
        ]

        url = self.patched_get_request_url(agent, "/benches/bench-1/status")

        self.assertEqual(url, "http://10.0.0.5:25052/benches/bench-1/status")

    def test_k3s_enabled_without_url_falls_back_to_default_flask_port(self):
        agent = FakeAgent("Server", "s1.example.com", 443)
        self.frappe.db.get_value.side_effect = [True, None]

        url = self.patched_get_request_url(agent, "ping")

        self.assertEqual(url, "http://127.0.0.1:25052/ping")

    def test_k3s_disabled_uses_official_https_form(self):
        agent = FakeAgent("Server", "s1.example.com", 443)
        self.frappe.db.get_value.side_effect = [
            False,  # custom_k3s_enabled
            ("1.2.3.4", "10.0.0.1", "Cluster-1"),  # ip, private_ip, cluster
        ]

        url = self.patched_get_request_url(agent, "ping")

        self.assertEqual(url, "https://s1.example.com:443/agent/ping")

    def test_missing_flag_does_not_break(self):
        agent = FakeAgent("Server", "s1.example.com", 443)
        self.frappe.db.get_value.side_effect = [
            None,  # custom_k3s_enabled field missing entirely
            ("1.2.3.4", "10.0.0.1", "Cluster-1"),
        ]

        url = self.patched_get_request_url(agent, "ping")

        self.assertEqual(url, "https://s1.example.com:443/agent/ping")

    def test_proxy_fallback_survives_missing_private_attribute(self):
        # Simulate a future Press release renaming/dropping Agent.__servers_using_alt_ports.
        agent = FakeAgent("Database Server", "db1.example.com", 443)
        self.frappe.flags.in_test = False
        self.frappe.db.get_value.side_effect = [
            (None, "10.0.0.1", "Cluster-1"),  # ip, private_ip, cluster -> needs proxy
            "proxy1",  # Proxy Server lookup
        ]

        url = self.patched_get_request_url(agent, "ping")

        self.assertEqual(url, "https://proxy1:443/db1.example.com:443/agent/ping")

    def test_proxy_uses_alt_port_when_attribute_present(self):
        agent = FakeAgent(
            "Database Server", "db1.example.com", 443, alt_port_servers={"proxy1"}
        )
        self.frappe.flags.in_test = False
        self.frappe.db.get_value.side_effect = [
            (None, "10.0.0.1", "Cluster-1"),
            "proxy1",
        ]

        url = self.patched_get_request_url(agent, "ping")

        self.assertEqual(url, "https://proxy1:8443/db1.example.com:443/agent/ping")


class ApplyAgentPatchTests(unittest.TestCase):
    def setUp(self):
        self.frappe = _install_fake_frappe()

        press_pkg = types.ModuleType("press")
        press_agent_mod = types.ModuleType("press.agent")

        class RealAgent:
            server_type = "Server"
            server = "s1"
            port = 443

            def _get_request_url(self, path):
                return f"https://official/{path}"

        press_agent_mod.Agent = RealAgent
        press_pkg.agent = press_agent_mod
        sys.modules["press"] = press_pkg
        sys.modules["press.agent"] = press_agent_mod
        self.RealAgent = RealAgent

        _reset_press_k3s_modules()

    def tearDown(self):
        for mod in ("press", "press.agent", "frappe"):
            sys.modules.pop(mod, None)
        _reset_press_k3s_modules()

    def test_patch_applies_and_is_idempotent(self):
        import press_k3s

        press_k3s.apply_agent_patch()
        self.assertTrue(getattr(self.RealAgent._get_request_url, "_press_k3s", False))

        patched_once = self.RealAgent._get_request_url
        press_k3s.apply_agent_patch()
        self.assertIs(self.RealAgent._get_request_url, patched_once)

    def test_disabled_flag_falls_back_to_official_form_via_patch(self):
        import press_k3s

        press_k3s.apply_agent_patch()
        agent = self.RealAgent()
        self.frappe.db.get_value.side_effect = [
            False,  # custom_k3s_enabled
            ("1.2.3.4", "10.0.0.1", "Cluster-1"),
        ]

        url = agent._get_request_url("ping")

        self.assertEqual(url, "https://s1:443/agent/ping")


if __name__ == "__main__":
    unittest.main()
