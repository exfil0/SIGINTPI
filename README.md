# SIGINTPI Wizard Setup

This document explains how to set up and run the **wizard** scripts in the `wizard/` folder of the SIGINTPI project.

## Overview

The **wizard** folder contains Python scripts that help automate:

1. **Raspberry Pi readiness** (basic updates, remote access, etc.)  
2. **Component readiness** (installing drivers for SDR devices like RTL-SDR, HackRF, etc.)  
3. **Software readiness** (installing GNU Radio, GQRX, GR-GSM, Kalibrate-RTL, etc.)

## 1. Clone the Repository

To get started, clone the SIGINTPI repository from GitHub:

```bash
git clone https://github.com/exfil0/SIGINTPI.git
cd SIGINTPI
```

## 2. Make the Scripts Executable

To run the Python scripts directly (without typing `python3`), make them executable. In your project’s root directory (or wherever your `wizard/` folder is located), run:

```bash
chmod +x wizard/*.py
```

This command applies executable permissions to all `.py` files in the `wizard/` directory. If you have subfolders with `.py` files, you can recursively apply permissions:

```bash
find wizard/ -type f -name "*.py" -exec chmod +x {} \;
```

**Note:** You can skip this step if you prefer to run each script with `python3 wizard/scriptname.py`.

Additionally, ensure that the required permissions are set on all scripts during deployment. Run the following command to ensure all scripts in the `wizard/` directory are ready to execute:

```bash
chmod -R +x wizard
```

## 3. Run the Scripts

You can execute each script in the `wizard` folder in sequence (or as needed):

### `raspberrypi_readiness.py`

- Performs basic Raspberry Pi system updates, upgrades, and enables SSH/VNC.

### `remote-access-enable.py`

- Specifically enables and checks remote access services (SSH, VNC).

### `raspberrypi-components-readiness.py`

- Installs drivers/packages for hardware (e.g., RTL-SDR, HackRF).
- Automatically detects devices (like HackRF, NESDR) and tests them.

### `raspberrypi-software-readiness.py`

- Installs & verifies signal-processing software (GNU Radio, GQRX, GR-GSM, Kalibrate-RTL).
- Prompts you to test GUI apps (e.g., GQRX) on the desktop.

### Examples

If you made the scripts executable:

```bash
cd wizard
./raspberrypi_readiness.py
./remote-access-enable.py
./raspberrypi-components-readiness.py
./raspberrypi-software-readiness.py
```

If you want to use Python directly:

```bash
cd wizard
python3 raspberrypi_readiness.py
python3 remote-access-enable.py
python3 raspberrypi-components-readiness.py
python3 raspberrypi-software-readiness.py
```

## 4. Follow On-Screen Prompts

During the setup, you might be prompted to:

- Reboot or log out/log in to apply certain changes (e.g., group memberships).
- Plug in devices (e.g., HackRF, NESDR). The script may wait until the device is detected (via `lsusb`).
- Open desktop-based tools (e.g., GNU Radio Companion, GQRX) to confirm they launch properly.

Read the console output carefully and follow each instruction.

## Troubleshooting

### Permission Denied

If you get a `Permission denied` error, ensure you have run `chmod +x` on the script or invoke it with `python3 wizard/<script>.py`.

### Missing Dependencies

Check that your system is online and up to date. The scripts typically run `sudo apt update -y && sudo apt upgrade -y` to ensure a fresh environment.

### Custom OS Differences

If you are using a custom Raspberry Pi OS, some packages or commands may differ. Modify the scripts or install missing packages manually if needed.

### Group Membership Issues

When a script adds your user to a group (e.g., `plugdev`), you must log out and log back in or reboot for the changes to apply.
