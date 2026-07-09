# SECRET ROTATION NOTE — R7

The user noted that an NVIDIA key was pasted into chat during the install window.

Recommended handling:

1. Rotate the NGC/NVIDIA key after the install window.
2. Keep runtime secrets only in restricted files such as mode `600`.
3. Do not package secrets into CityBrain artifacts.
4. Do not log Authorization headers or environment values.
5. Secret audit should scan for common token prefixes, bearer headers, API key names, and long opaque strings.
