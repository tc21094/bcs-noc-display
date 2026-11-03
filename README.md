# BCS NOC display setup

Turns an Intel Mac mini running Ubuntu 26.04 into a BCS NOC dashboard display, and gives you one command (`noc`) to control every display at once.

![Boot splash](docs/preview_static.png)

## Set up a display

On the mini, with wired Ethernet plugged in, logged in as the account that should auto-login:

```bash
curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/install.sh | sudo bash -s -- --name noc-1 --url "https://your-dashboard"
```

Then `sudo reboot`. At the end it prints the line to register the display with `noc`.

What it does:

- Installs the Broadcom Wi-Fi driver (skipped if there's no Broadcom card or it already works)
- Installs the animated BCS NOC boot splash and a 4K desktop wallpaper
- With `--url`: auto-login, fullscreen Chrome on the dashboard, no screen blanking/lock/sleep, update and crash popups silenced, SSH, auto power-on after an outage, nightly 4 AM reboot, and the `kiosk` / `noc` control commands

| Option | Effect |
|---|---|
| `--url URL` | Dashboard to show fullscreen (turns on kiosk setup) |
| `--name NAME` | Set the display's hostname, e.g. `noc-1` |
| `--user NAME` | Account that auto-logs in (default: whoever ran sudo) |
| `--no-wifi` | Skip the Broadcom driver |
| `--no-splash` | Skip the boot splash and wallpaper |
| `--reboot` | Reboot when finished |

## Control every display with `noc`

Install on your Mac or Linux machine (each display also has it):

```bash
sudo curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/bin/noc -o /usr/local/bin/noc && sudo chmod +x /usr/local/bin/noc
```

One-time setup:

```bash
noc add noc-1 tc@10.0.0.21      # name, then login@address for each display
noc add noc-2 tc@10.0.0.22
noc add noc-3 tc@10.0.0.23
noc keys                        # password-free SSH (asks each display's password once)
```

Everyday use. `TARGET` is `all` (the default), a name, a number from `noc list`, or a list like `1,3`:

```bash
noc                     # status of every display
noc stop                # take manual control: dashboards close on all three
noc start               # put them back
noc restart 2           # reload display 2
noc url                 # what each display shows
noc url 2 https://...   # change display 2's dashboard
noc disable 3           # keep display 3 off, even across reboots (noc enable 3 to undo)
noc reboot              # reboot all (asks first)
noc run all 'uptime'    # run any command everywhere
noc ssh 1               # shell on display 1
noc update              # re-run this installer on every display (asks for sudo password)
```

On a display itself, `kiosk help` lists the same controls (`kiosk stop`, `kiosk url ...`, etc).

A stopped dashboard comes back at the next reboot (including the 4 AM one). Use `disable` to keep it off.

## Upgrading a display that ran an older version

```bash
curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/install.sh | sudo bash -s -- --name noc-1 --url "$(cat /etc/bcs-noc-dashboard-url)"
sudo reboot
```

`$(cat /etc/bcs-noc-dashboard-url)` reuses the dashboard the display already has. If the display was set up with the very first `kiosk-setup.sh` (no such file), type the URL instead.

## Rebuilding

`src/` holds the boot theme and wallpaper generators, `bin/` the control scripts. With python3, pillow, numpy and scipy:

```bash
cd src && ./make_installer.sh   # writes ../install.sh
```

Splash recording: `docs/bcs-noc-boot-preview.mp4`. Orbitron font: SIL Open Font License.
