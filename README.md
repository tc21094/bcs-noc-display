# BCS NOC display setup

Turns an Intel Mac mini running Ubuntu 26.04 into a BCS NOC dashboard display.

![Boot splash](docs/preview_static.png)

## Install

On the mini, with wired Ethernet plugged in:

```bash
curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/install.sh | sudo bash -s -- --url "https://your-dashboard"
```

Then `sudo reboot`.

## What it does

- Installs the Broadcom Wi-Fi driver (skipped if there's no Broadcom card or it already works)
- Installs the animated BCS NOC boot splash and a matching desktop wallpaper
- With `--url`: auto-login, fullscreen Chrome kiosk on the dashboard, no screen blanking/lock/sleep, update and crash popups silenced, SSH, auto power-on after an outage, nightly 4 AM reboot

## Options

| Option | Effect |
|---|---|
| `--url URL` | Dashboard to show fullscreen (turns on kiosk setup) |
| `--user NAME` | Account that auto-logs in (default: whoever ran sudo) |
| `--no-wifi` | Skip the Broadcom driver |
| `--no-splash` | Skip the boot splash and wallpaper |
| `--reboot` | Reboot when finished |

Re-run any time, e.g. with a new `--url` to change the dashboard.

## Rebuilding the splash

`src/` holds the theme generator. With python3, pillow, numpy and scipy:

```bash
cd src && ./make_installer.sh logo.png Orbitron.ttf   # writes dist/install.sh
```

A recording of the splash is in `docs/bcs-noc-boot-preview.mp4`.

Orbitron font: SIL Open Font License.
