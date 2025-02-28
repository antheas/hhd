<h1 align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hhd-dev/hhd/master/art/logo_dark.svg" width="50%">
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/hhd-dev/hhd/master/art/logo_light.svg" width="50%">
        <img alt="Handheld Daemon Logo." src="https://raw.githubusercontent.com/hhd-dev/hhd/master/art/logo_light.svg" width="50%">
    </picture>
</h1>

[![PyPI package version](https://badge.fury.io/py/hhd.svg)](https://pypi.org/project/hhd/)
[![Python version 3.12+](https://img.shields.io/badge/python-3.12%2B-informational.svg)](https://pypi.org/project/pasteur/)
[![Code style is Black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)
<!-- [![]()]() -->

# Handheld Daemon
Handheld Daemon provides hardware enablement for Windows handhelds, so that they run correctly in Linux. It acts as a vendor interface replacement (e.g., Armoury Crate equivalent), with fan curves, TDP controls, controller emulation including gyro, back buttons, and SteamOS shortcuts, and RGB remapping. All of this is through a gamescope overlay, accessible through double tapping the side menu button of the device, and a desktop app.

## Showcase
![Overlay](./docs/overlay.gif)

## <a name="devices"></a>Supported Devices
Handheld Daemon features great support for Lenovo, Asus, GPD, OneXPlayer, and Ayn. It also features some support for Ayaneo devices, Anbernic, and MSI. We aim to support new models by these manufacturers as they release, so if you don't see your device below, chances are it will still work or just needs to have its config included.

- Lenovo Legion
  - Go
  - Go S
- Asus ROG
  - Ally
  - Ally X
- GPD Win (all model years)
  - Win 4
  - Win Mini
  - Win Max 2
- OneXPlayer
  - X1 (AMD, Intel w/o TDP)
  - X1 Mini
  - F1, F1 EVA-01, F1L, F1 OLED, F1 Pro
  - 2, 2 APR23, 2 PRO APR23, 2 PRO APR23 EVA-01
  - Mini A07
  - Mini Pro
  - ONE XPLAYER
- MSI
  - Claw 1st Gen, 7/8 AI+ (only front buttons; suspend issues)
- Zotac
  - Zotac Gaming Zone (1st gen; only front buttons)
- Ayn
  - Loki MiniPro/Zero/Max
- Ayaneo
  - Air Standard/Plus/Pro
  - 1S/1S Limited
  - 2/2S 
  - GEEK, GEEK 1S 
  - NEXT Lite/Pro/Advance
  - SLIDE
  - 2021 Standard/Pro/Pro Retro Power
  - NEO 2021/Founder
  - KUN (only front buttons)
- AOKZOE (No LEDs)
  - A1 Normal/Pro
- Anbernic
  - Win600 (no keyboard button yet)
- TECNO
  - Pocket Go (all buttons except bottom switch and gyro; no RGB)

## Installation Instructions
For Arch and Fedora see [here](#os-install).
For others, you can use the following script to install a local version of
Handheld Daemon that updates independently of the system.
```bash
curl -L https://github.com/hhd-dev/hhd/raw/master/install.sh | bash
```

This script does not automatically install system dependencies.
A partial list for Ubuntu/Debian can be found [here](#debian).
This includes `acpi_call` for TDP on devices other than the Ally.
For all devices, use the [bazzite kernel](https://github.com/hhd-dev/kernel-bazzite)
for best support or Bazzite. Some caveats for certain devices are listed below.

### Uninstall
We are sorry to see you go, use the following to uninstall:
```bash
curl -L https://github.com/hhd-dev/hhd/raw/master/uninstall.sh | bash
```

### Using an older version
If you find any issues with the latest version of Handheld Daemon
you can use any version by specifying it with the command below.
```bash
sudo systemctl stop hhd_local@$(whoami)
~/.local/share/hhd/venv/bin/pip install hhd==2.6.0
sudo systemctl start hhd_local@$(whoami)
```

### <a name="issues"></a>After Install Instructions

#### Extra steps for ROG Ally
You can hold the ROG Crate button to switch to the ROG Ally's Mouse mode to turn
the right stick into a mouse.

Combinations with the ROG, Armory Crate buttons is not supported in the Ally,
but you can use ROG swap for that.

#### Extra steps GPD Win Devices
Swipe the left top of the screen to show handheld daemon in gamescope or open
the desktop app and head to the WinControls tab. There, press apply to remap
the back buttons correctly.

For the GPD Win 4, the Menu button is used as a combo (Short Pres QAM,
long press Xbox button, double press hhd) and select can be used for
SteamOS chords (e.g., Select + RT is screenshot). For other devices, the R4 
button is used to bring up QAM (single tap), and HHD (double tap/hold).
You can customize to your tastes in the Controller section.

#### Extra steps for Ayaneo/Ayn
You might experience a tiny amount of lag with the Ayaneo LEDs.
The paddles of the Ayn Loki Max are not remappable as far as we know.

#### Extra steps for Legion Go
If you have set any mappings on Legion Space, they will interfere with Handheld
Daemon.
You can factory reset the Controllers from the Handheld Daemon settings.

The controller gyros of the Legion Go tend to drift sometimes. Calibrate them
with the built-in calibration by pressing LT + LS and RT + RS, then turning
the Joysticks twice and pressing the triggers. Finally, the controllers will
vibrate and flash the leds, zeroing the gyroscope.

## <a name="os-install"></a> Distribution Install
You can install Handheld Daemon from [AUR](https://aur.archlinux.org/packages/hhd) 
(Arch) or [COPR](https://copr.fedorainfracloud.org/coprs/hhd-dev/hhd/) (Fedora).
Both update automatically every time there is a new release.
For Debian/Ubuntu see below.

```bash
# Arch
yay -S hhd adjustor hhd-ui

# Fedora
sudo dnf copr enable hhd-dev/hhd
sudo dnf install hhd adjustor hhd-ui

sudo systemctl enable hhd@$(whoami)
```

### <a name="debian"></a> Debian/Ubuntu
The following packages are required for local install to work on Ubuntu/Debian.
Handheld daemon is not packaged for apt yet.
```bash
sudo apt install \
    libgirepository1.0-dev \
    libcairo2-dev \
    libpython3-dev \
    python3-venv \
    libhidapi-hidraw0
```

### ❄️ NixOS
Handheld Daemon (core and overlay, no TDP) is on `nixpkgs` in the `unstable` channel.

Add the following to your `configuration.nix` to enable:
```nix
  services.handheld-daemon = {
    enable = true;
    user = "<your-user>";
    ui.enable = true;
  };
```

### <a name="bazzite"></a><a name="after-install"></a>Bazzite
Handheld Daemon comes pre-installed on [Bazzite](https://bazzite.gg) and 
updates along-side the system.
Most users of Handheld Daemon are on Bazzite and Bazzite releases
often happen for Handheld Daemon to update.
Bazzite contains all kernel patches and quirks required for all supported handhelds
to work (to the extent they can; certain Ayaneo devices have issues).

If you want to test the development Handheld Daemon version you
can use `ujust _hhd-dev` and give feedback.
It will only last until you reboot and leave no changes to your system.
After changes are deemed stable, they usually are incorporated to Bazzite
after a few days.

See [supported devices](#supported-devices) to check the status of your device and 
[after install](#issues) for specific device quirks.

## Contributing
### <a name="axis"></a> Finding the correct axis for your device
To figure the correct axis from your device, go to steam calibration settings.
Then, in the overlay (double press/hold side button) switch `Motion Axis` to 
`Override` and tweak only the axis (without invert) of your device until they 
match the glyphs in steam.

Then, jump in a first person game and turn on `Gyro to Mouse` or `Camera`.
By default (`Yaw`), rotating your device like a steering wheel should turn left 
to right,
and rotating it to face down or up should look up or down.
Fix the invert settings of the axis so that it is intuitive.
Finally, switch the setting `Gyro Turning Axis` from `Yaw` (rotate like a steering
wheel) to `Roll` (turn left to right), and fix the remaining axis inversion.

You can now either take a picture of your screen or translate the settings into
text (e.g., x is k, y is l inverted, z is j) and open an issue.
The override setting also displays the make and model of your device, which
are required to add the mappings to Handheld Daemon.

### Localizing Handheld Daemon
Handheld Daemon fully supports localization through standard `PO`, `POT` files.
Contribution instructions in progress!!!

#### For maintainers
You can find `pot` and `po` files for Handheld Daemon under the `i18n` directory.
You can clone/download this repository and open the `./i18n` directory.
Then, just copy the `*.pot` files into `<your_locale>/LC_MESSAGES/*.po`
and begin translating with your favorite text editor, or by using
tool such as [Lokalize](https://apps.kde.org/lokalize/).

As far as your locale goes, unless you have a good reason to, skip the territory
code (e.g., `el` instead of `el_GR`).

The files can be updated for a new version with the following commands:
```bash
# Prepare dev environment
git clone https://github.com/hhd-dev/hhd
cd hhd
python -m venv venv
pip install babel
pip install -e .

# Regenerate POT files
pybabel extract --no-location -F i18n/babel.cfg -o i18n/hhd.pot src/hhd
# Assuming adjustor is in an adjacent directory
pybabel extract --no-location -F i18n/babel.cfg -o i18n/adjustor.pot ../adjustor/src/adjustor

YOUR_LANG=el

# Generate PO files for your language if they do not exist
pybabel init -i i18n/hhd.pot -d i18n -D hhd -l $YOUR_LANG
pybabel init -i i18n/adjustor.pot -d i18n -D adjustor -l $YOUR_LANG

# Update current PO files for your language
pybabel update -i i18n/hhd.pot -d i18n -D hhd -l $YOUR_LANG
pybabel update -i i18n/adjustor.pot -d i18n -D adjustor -l $YOUR_LANG
```

### Creating a Local Repo version
Either follow `Automatic Install` or `Manual Local Install` to install the base rules.
Then, clone, optionally install the userspace rules, and run.
```bash
# Clone Handheld Daemon
git clone https://github.com/hhd-dev/hhd
cd hhd
python -m venv venv
source venv/bin/activate
pip install -e .

# Install udev rules to allow running without sudo (optional)
# but great for debugging (not all devices will run properly, the rules need to be expanded)
sudo curl https://raw.githubusercontent.com/hhd-dev/hhd/master/usr/lib/udev/rules.d/83-hhd-user.rules -o /etc/udev/rules.d/83-hhd-user.rules
# Modprobe uhid to avoid rw errors
sudo curl https://raw.githubusercontent.com/hhd-dev/hhd/master/usr/lib/modules-load.d/hhd-user.conf -o /etc/modules-load.d/hhd-user.conf
# You can now run hhd in userspace!
hhd

# Use the following to run with sudo
sudo hhd --user $(whoami)
```

# License
Handheld Daemon is licensed under THE GNU GPLv3+. See LICENSE for details.
A small number of files are dual licensed with MIT, and contain
SPDX headers denoting so. 
Versions prior to and excluding 2.0.0 are licensed using MIT.

# Credits
Much like a lot of open-source projects, Handheld Daemon is a community effort.
It relies on the kernel drivers 
[oxp-sensors](https://github.com/torvalds/linux/blob/master/drivers/hwmon/oxp-sensors.c), [ayn-platform](https://github.com/ShadowBlip/ayn-platform), 
[ayaneo-platform](https://github.com/ShadowBlip/ayaneo-platform), 
[bmi260](https://github.com/hhd-dev/bmi260), [gpdfan](https://github.com/Cryolitia/gpd-fan-driver/),
and [asus-wmi](https://github.com/torvalds/linux/blob/master/drivers/platform/x86/asus-wmi.c).
In addition, certain parts of Handheld Daemon reference the reverse engineering
efforts of [asus-linux](https://gitlab.com/asus-linux), 
the [Handheld Companion](https://github.com/Valkirie/HandheldCompanion) project,
the [ValvePython](https://github.com/ValvePython) project, [pyWinControls](https://github.com/pelrun/pyWinControls), and the [HandyGCCS](https://github.com/ShadowBlip/HandyGCCS) project.
Finally, its functionality is made possible thanks to thousands of hours of 
volunteer testing, who have provided feedback and helped shape the project.
Some of those volunteers integrated support for their devices directly, especially
in the case of Ayaneo, GPD, and for the initial support of OneXPlayer, and ROG Ally
devices.
