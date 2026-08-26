from __future__ import annotations

import frappe


def patched_get_request_url(self, path: str) -> str:
    """Same contract as press.agent.Agent._get_request_url, with a k3s escape hatch."""
    if self.server_type == "Server" and self.server:
        enabled = frappe.db.get_value("Server", self.server, "custom_k3s_enabled")
        if enabled:
            base = (
                frappe.db.get_value("Server", self.server, "custom_k3s_agent_url")
                or "http://127.0.0.1:25052"
            ).rstrip("/")
            # Field is the Flask origin. Official Press nginx adds /agent/;
            # kagent flask routes live at the root (/ping, /benches/...).
            return f"{base}/{path.lstrip('/')}"

    if self.server_type in ("Server", "Database Server"):
        proxy = None
        server_ip, server_private_ip, server_cluster = frappe.db.get_value(
            self.server_type, self.server, ("ip", "private_ip", "cluster")
        )
        if not server_ip and server_private_ip and not frappe.flags.in_test:
            proxy = frappe.db.get_value(
                "Proxy Server",
                {
                    "status": "Active",
                    "cluster": server_cluster,
                    "use_as_proxy_for_agent_and_metrics": 1,
                },
            )
        if proxy:
            # Name-mangled private attribute on press.agent.Agent; fall back to an
            # empty set (i.e. always port 443) if a future Press release renames
            # or drops it, rather than raising AttributeError on every request.
            alt_port_servers = getattr(self, "_Agent__servers_using_alt_ports", frozenset())
            proxy_port = 8443 if proxy in alt_port_servers else 443
            return f"https://{proxy}:{proxy_port}/{self.server}:{self.port}/agent/{path}"

    return f"https://{self.server}:{self.port}/agent/{path}"
