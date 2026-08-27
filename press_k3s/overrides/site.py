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


def build_patched_process_new_site_job_update(original):
    """Wrap process_new_site_job_update.

    Stock Press only sets Site Active when New Site *and* Add Site to Upstream
    both succeed. k3s skips the proxy upstream job, so treat New Site Success
    as enough to activate.
    """

    def patched_process_new_site_job_update(job):
        site_name = getattr(job, "site", None)
        job_type = getattr(job, "job_type", None)
        status = getattr(job, "status", None)
        if site_name and job_type in ("New Site", "New Site from Backup") and status == "Success":
            server = frappe.db.get_value("Site", site_name, "server")
            if server and frappe.db.get_value("Server", server, "custom_k3s_enabled"):
                current = frappe.db.get_value("Site", site_name, "status")
                if current != "Active":
                    site = None
                    try:
                        from press.press.doctype.site.site import Site as PressSite

                        site = PressSite("Site", site_name)
                    except Exception:
                        site = None
                    if site is not None:
                        for method in ("sync_apps", "enable_subscription"):
                            fn = getattr(site, method, None)
                            if callable(fn):
                                try:
                                    fn()
                                except Exception:
                                    pass
                    frappe.db.set_value("Site", site_name, "status", "Active")
                return None
        return original(job)

    patched_process_new_site_job_update._press_k3s = True
    return patched_process_new_site_job_update
