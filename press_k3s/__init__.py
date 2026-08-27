__version__ = "0.0.1"


def apply_agent_patch():
    try:
        from press.agent import Agent
        from press_k3s.overrides.agent import patched_get_request_url
    except Exception:
        return

    current = getattr(Agent, "_get_request_url", None)
    if current is None or getattr(current, "_press_k3s", False):
        return
    patched_get_request_url._press_k3s = True
    Agent._get_request_url = patched_get_request_url


def apply_site_patch():
    try:
        from press.press.doctype.site.site import Site
        from press_k3s.overrides.site import build_patched_create_agent_request
    except Exception:
        return

    current = getattr(Site, "create_agent_request", None)
    if current is None or getattr(current, "_press_k3s", False):
        return
    Site.create_agent_request = build_patched_create_agent_request(current)


apply_agent_patch()
apply_site_patch()
