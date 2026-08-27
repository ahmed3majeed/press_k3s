from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock


def _install_fake_frappe():
    fake = types.ModuleType("frappe")
    fake.db = MagicMock()
    fake.flags = types.SimpleNamespace(in_test=True)
    sys.modules["frappe"] = fake
    return fake


def _install_fake_press_agent():
    """press_k3s.overrides.site does `from press.agent import Agent` lazily."""
    press_pkg = sys.modules.get("press") or types.ModuleType("press")
    press_agent_mod = types.ModuleType("press.agent")
    agent_instance = MagicMock()
    agent_cls = MagicMock(return_value=agent_instance)
    press_agent_mod.Agent = agent_cls
    press_pkg.agent = press_agent_mod
    sys.modules["press"] = press_pkg
    sys.modules["press.agent"] = press_agent_mod
    return agent_cls, agent_instance


def _reset_press_k3s_modules():
    for mod in ("press_k3s.overrides.site", "press_k3s.overrides", "press_k3s"):
        sys.modules.pop(mod, None)


class FakeSite:
    def __init__(self, server, remote_database_file=None):
        self.server = server
        self.remote_database_file = remote_database_file
        self.name = "site1.example.com"


class BuildPatchedCreateAgentRequestTests(unittest.TestCase):
    def setUp(self):
        self.frappe = _install_fake_frappe()
        self.agent_cls, self.agent_instance = _install_fake_press_agent()
        _reset_press_k3s_modules()
        from press_k3s.overrides.site import build_patched_create_agent_request

        self.original = MagicMock(name="original_create_agent_request")
        self.patched = build_patched_create_agent_request(self.original)

    def tearDown(self):
        for mod in ("press", "press.agent", "frappe"):
            sys.modules.pop(mod, None)
        _reset_press_k3s_modules()

    def test_k3s_disabled_calls_original_unchanged(self):
        self.frappe.db.get_value.return_value = False
        site = FakeSite(server="s1.example.com")

        self.patched(site)

        self.original.assert_called_once_with(site)
        self.agent_cls.assert_not_called()

    def test_k3s_enabled_calls_new_site_not_upstream_file(self):
        self.frappe.db.get_value.return_value = True
        site = FakeSite(server="k3s-test.None")

        self.patched(site)

        self.original.assert_not_called()
        self.agent_cls.assert_called_once_with("k3s-test.None")
        self.agent_instance.new_site.assert_called_once_with(site)
        self.agent_instance.new_site_from_backup.assert_not_called()
        self.agent_instance.new_upstream_file.assert_not_called()

    def test_k3s_enabled_with_backup_calls_new_site_from_backup(self):
        self.frappe.db.get_value.return_value = True
        site = FakeSite(server="k3s-test.None", remote_database_file="db.sql.gz")

        self.patched(site)

        self.agent_instance.new_site_from_backup.assert_called_once()
        self.agent_instance.new_site.assert_not_called()
        self.agent_instance.new_upstream_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
