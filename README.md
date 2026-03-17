> Exploring `systemd` in Linux

Setup a systemd service to change the wallpaper every X minutes. The wallpaper is soured from Unsplash via their API.
We can provide filters/categories to the API.

## Table of Contents

[1. Registering the service](#1-registering-the-service)

[2. Starting the service](#2-starting-the-service)

[3. Viewing the logs](#3-viewing-the-logs)

Firstly, Setup the python environment and install the dependencies from [requirements.txt](./requirements.txt) file.

### 1. Registering the service

```bash
# copy the .service file to the systemd user directory
~/.config/systemd/user/unsplash-wallpaper.service
```

and reload the systemd daemon:

```bash
systemctl --user daemon-reload
```

### 2. Starting the service

```bash
systemctl --user start unsplash-wallpaper.service
```

```bash
# persists across reboots
systemctl --user enable unsplash-wallpaper.service
```

### 3. Viewing the logs

```bash
systemctl --user status unsplash-wallpaper.service
# or
journalctl --user -u unsplash-wallpaper.service -f
```
