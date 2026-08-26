app_name = "press_k3s"
app_title = "Press K3s"
app_publisher = "Ahmed"
app_description = "Drive kagent (k3s) from Frappe Press"
app_email = "ahmed3mageed@gmail.com"
app_license = "agpl-3.0"
required_apps = ["press"]

after_install = "press_k3s.install.after_install"
after_migrate = "press_k3s.install.after_migrate"
