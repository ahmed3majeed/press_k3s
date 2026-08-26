# press_k3s

Custom [Frappe Press](https://github.com/frappe/press) app that talks to
[kagent](https://github.com/ahmed3majeed/kagent) (k3s) instead of the official
Docker Frappe Agent.

AGPL-3.0. Same license family as Press and Agent.

## What it does

Press's `Agent` client always calls `https://{server}:{443|8443}/agent/...`.
A k3s worker is not that: kagent listens on the host (dev default
`http://127.0.0.1:25052`) and executes into pods.

This app:

1. Adds **K3s Settings** plus two fields on **Server**: `K3s Enabled`, `K3s Agent URL`.
2. Patches `press.agent.Agent._get_request_url` so enabled servers hit that URL.
3. Does **not** fork Press. Disable the app and Press is stock again.

## Install (after Press exists)

```bash
cd /home/frappe/frappe-bench
bench get-app press_k3s https://github.com/ahmed3majeed/press_k3s
bench --site press.localhost install-app press_k3s
```

Then on the Server that owns the k3s box: check **K3s Enabled** and set
**K3s Agent URL** (example: `http://127.0.0.1:25052`). Set `agent_password` to
the same token kagent hashes in `config.json`.

## MVP jobs

Unchanged Press job names — kagent already implements the agent HTTP contract
for site create / migrate / backup / restore once `docker_execute` is k8s-backed.

Ansible VM provisioning is out of scope. Register an already-running kagent;
do not click Press "Provision Server".
