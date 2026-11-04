# BCS NOC display setup

Turns an Intel Mac mini running Ubuntu 26.04 into a BCS NOC dashboard display, and gives you one command (`noc`) to control every display at once.

![Boot splash](docs/preview_static.png)

## Set up a display

On the mini, with wired Ethernet plugged in, logged in as the account that should auto-login:

```bash
curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/install.sh | sudo bash -s -- --name noc-1 --url "https://your-dashboard"
```

Then `sudo systemctl reboot -i` (plain `sudo reboot` is blocked while the desktop is logged in). At the end it prints the line to register the display with `noc`.

What it does:

- Installs the Broadcom Wi-Fi driver (skipped if there's no Broadcom card or it already works)
- Installs the animated BCS NOC boot splash and a 4K desktop wallpaper
- With `--url`: auto-login, fullscreen Chrome on the dashboard, no screen blanking/lock/sleep, update and crash popups silenced, SSH, auto power-on after an outage, nightly 4 AM reboot, the BCS NOC interlude (below), and the `kiosk` / `noc` control commands

| Option | Effect |
|---|---|
| `--url URL` | Dashboard to show fullscreen (turns on kiosk setup) |
| `--name NAME` | Set the display's hostname, e.g. `noc-1` |
| `--interlude MIN` | Play the BCS NOC interlude every MIN minutes (default 30, `0` = off) |
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
noc reload 2            # reload display 2's page
noc restart 2           # restart Chrome on display 2
noc interlude           # play the BCS NOC interlude on every screen now
noc interlude every 20  # change how often it plays (0 = off)
noc blanket on          # "BCS Technology Department" on every screen until 'noc blanket off'
noc link                # let the bottom-left hot corner on any display toggle the blanket on all
noc url                 # what each display shows
noc url 2 https://...   # change display 2's dashboard (give several URLs to rotate)
noc rotate every 5      # rotate dashboards every 5 minutes, with a fade
noc disable 3           # keep display 3 off, even across reboots (noc enable 3 to undo)
noc reboot              # reboot all (asks first)
noc run all 'uptime'    # run any command everywhere
noc ssh 1               # shell on display 1
noc update              # re-run this installer on every display (asks for sudo password)
```

On a display itself, `kiosk help` lists the same controls (`kiosk stop`, `kiosk url ...`, etc).

A stopped dashboard comes back at the next reboot (including the 4 AM one). Use `disable` to keep it off.

## Rotating dashboards

Give a display several URLs and it rotates through them, fading to dark and back between each one:

```bash
noc url 2 https://grafana/d/core https://grafana/d/wifi https://unifi/dashboard
noc rotate every 5          # every display with more than one URL switches every 5 minutes
noc rotate 2 every 2        # or just display 2
noc next                    # switch now
noc rotate off              # stop rotating (noc next still steps through by hand)
```

Each dashboard stays open in its own background tab and keeps running, so the switch is instant and nothing reloads. That costs memory: each dashboard is a separate Chrome tab, so on a 4 GB display keep the list short. Switches happen on clock boundaries (every 5 minutes means :00, :05, :10 ...), so displays with the same interval switch together. Rotation pauses while the blanket is up and waits for an interlude to finish.

At setup: repeat `--url` for each dashboard and add `--rotate MIN`. Re-running the installer without `--url` keeps a display's current dashboards.

## BCS NOC interlude (burn-in protection)

Every 30 minutes, on the clock (:00 and :30), each display plays a 12-second full-screen animation over its dashboard, then fades back: circuit lanes route in from the screen edges toward the BCS B and spark at a small break around it, over a dot grid (style adapted from a colleague's maintenance-page animation, with our logo and colors). All displays play together because they follow the clock. The dashboard page keeps running underneath and is not reloaded.

It's drawn into the page through Chrome's DevTools pipe, so it works with any dashboard, including ones that refuse to be embedded or have strict security headers. It loads nothing from the network.

Change it with `noc interlude every N` (or `kiosk interlude every N` on a display). `0` turns it off. To change the length, edit the second number in `/etc/bcs-noc-interlude` (6-60 seconds).

## Blanket: "BCS Technology Department" on every screen

```bash
noc blanket on        # all displays
noc blanket off
noc blanket toggle
noc blanket           # show which displays have it on
```

The blanket is the same scene with "BCS / TECHNOLOGY DEPARTMENT", and it stays up until it's turned off, including through page reloads and reboots. The whole scene drifts a few pixels over several minutes, so it can't burn in either. Scheduled interludes are skipped while it's up.

**Hot corner:** move the mouse into the bottom-left corner of any display to toggle the blanket. Run this once so a corner on any display toggles all of them:

```bash
noc link
```

`noc link` gives every display the same random key and the list of the others. The displays send each other signed messages (UDP port 47474), so nobody else on the network can trigger it. Before `noc link`, a hot corner only affects its own display. Run `noc link` again after adding or re-addressing a display.

## Upgrading a display that ran an older version

```bash
curl -fsSL https://raw.githubusercontent.com/tc21094/bcs-noc-display/main/install.sh | sudo bash -s -- --name noc-1
sudo systemctl reboot -i
```

Without `--url` it keeps the dashboards the display already has. If the display was set up with the very first `kiosk-setup.sh`, add `--url` with its dashboard.

## Rebuilding

`src/` holds the boot theme and wallpaper generators, `bin/` the control scripts. With python3, pillow, numpy and scipy:

```bash
cd src && ./make_installer.sh   # writes ../install.sh
```

Recordings: `docs/bcs-noc-boot-preview.mp4` (boot splash), `docs/bcs-noc-interlude-preview.mp4`, `docs/bcs-blanket-preview.mp4`. Orbitron font: SIL Open Font License.
