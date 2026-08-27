from __future__ import annotations

import frappe


def build_patched_create_agent_request(original):
    """Wrap press.press.doctype.site.site.Site.create_agent_request.

    On k3s-enabled servers there is no Proxy Server / Traefik upstream file to
    write, so skip that call and talk to kagent directly. Non-k3s servers keep
    the original Press behaviour untouched.
    """

    def patched_create_agent_request(self):
        if not frappe.db.get_value("Server", self.server, "custom_k3s_enabled"):
            return original(self)

        from press.agent import Agent

        agent = Agent(self.server)
        if getattr(self, "remote_database_file", None):
            job = agent.new_site_from_backup(
                self, skip_failing_patches=getattr(self, "skip_failing_patches", False)
            )
        else:
            job = agent.new_site(self)
        if job is not None:
            flags = getattr(self, "flags", None)
            if flags is None:
                from types import SimpleNamespace

                flags = SimpleNamespace()
                self.flags = flags
            flags.new_site_agent_job_name = getattr(job, "name", job)
        return job

    patched_create_agent_request._press_k3s = True
    return patched_create_agent_request
