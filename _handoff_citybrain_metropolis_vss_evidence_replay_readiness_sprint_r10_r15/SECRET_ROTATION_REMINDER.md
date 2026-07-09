# Secret Rotation Reminder

The NVIDIA/NGC key was pasted during the previous install window.

Before wider sharing or production-like testing:
- rotate the key
- verify no secret appears in packages
- keep secret files mode 600
- refer to secrets by path or secret ref only
- do not include token values in JSON, logs, README files, or manifests
