#!/usr/bin/bash
# Installs Handheld Daemon to ~/.local/share/hhd

if [ "$EUID" -eq 0 ]
  then echo "You should run this script as your user, not root (sudo)."
  exit
fi

# Install Handheld Daemon to ~/.local/share/hhd
mkdir -p ~/.local/share/hhd && cd ~/.local/share/hhd

python -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade hhd

# Install udev rules and create a service file
sudo curl https://raw.githubusercontent.com/hhd-dev/hhd/master/usr/lib/udev/rules.d/83-hhd.rules -o /etc/udev/rules.d/83-hhd.rules
sudo curl https://raw.githubusercontent.com/hhd-dev/hhd/master/usr/lib/systemd/system/hhd_local%40.service -o /etc/systemd/system/hhd_local@.service

# Add hhd to user path
mkdir -p ~/.local/bin
ln -s ~/.local/share/hhd/venv/bin/hhd ~/.local/bin/hhd

# Start service and reboot
sudo systemctl enable hhd_local@$(whoami)

echo ""
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "!!! Do not forget to remove HandyGCCS/Bundled HHD if your distro preinstalls it. !!!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo ""
echo "Reboot to start Handheld Daemon!"