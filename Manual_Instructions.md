# **[GSM] FalconOne IMSI/TMSI and SMS Catcher Blueprint V1**

## **Research & Development Team**

| Version | Status |
|---------|--------|
| 1.0     | **TOP CONFIDENTIAL** |

---

![Blueprint Image][image1]

## **Table of Contents**

1. [Introduction](#introduction)
2. [Blueprint](#blueprint)
    - [Required Equipment](#required-equipment)
        - [Final Product Components](#final-product-components)
        - [Setup and Management Equipment](#setup-and-management-equipment)
        - [Optional Equipment](#optional-equipment)
3. [Core Infrastructure Setup (Stage 1)](#core-infrastructure-setup-stage-1)
    - [Network Setup and Initial Configurations](#network-setup-and-initial-configurations)
    - [Imaging the Raspberry Pi OS](#imaging-the-raspberry-pi-os)
    - [Starting and Connecting to the Raspberry Pi 5](#starting-and-connecting-to-the-raspberry-pi-5)
4. [Raspberry Pi 5 Readiness (Stage 1)](#raspberry-pi-5-readiness-stage-1)
    - [Initial System Setup](#initial-system-setup)
    - [Installing Essential Python Packages](#installing-essential-python-packages)
5. [Raspberry Pi 5 and Components Readiness (Stage 2)](#raspberry-pi-5-and-components-readiness-stage-2)
6. [Raspberry Pi 5 and Software Readiness (Stage 2)](#raspberry-pi-5-and-software-readiness-stage-2)
7. [Raspberry Pi 5 and Software Readiness (Stage 3)](#raspberry-pi-5-and-software-readiness-stage-3)
    - [TShark Installation and Configuration](#tshark-installation-and-configuration)
    - [Setting Up Permissions for Non-Root Capture](#setting-up-permissions-for-non-root-capture)
    - [Capturing IMSI and SMS Data](#capturing-imsi-and-sms-data)

---

## **Introduction**

The FalconOne IMSI/TMSI and SMS Catcher blueprint provides a structured approach to deploying a GSM monitoring system using Raspberry Pi 5 along with HackRF One or NESDR Smart by Nooelec. This document outlines the necessary hardware, network configuration, software installations, and operational steps required to effectively capture IMSI, TMSI, and SMS data in real-time environments.

This system is intended for authorized law enforcement, security professionals, and researchers conducting GSM traffic analysis. The guide details precise installation steps, permission settings, and optimized command-line tools to ensure seamless data collection and monitoring.

---

## **Blueprint**

### **Required Equipment**

#### **Final Product Components**
The following hardware is required for the final build:

- Raspberry Pi 5
- SD card (200GB+ capacity)
- LAN cable
- Original Raspberry Pi 5 USB-C power adapter (or power bank)
- NESDR Smart by Nooelec kit (including antennas) **or** HackRF One Kit

#### **Setup and Management Equipment**
The following equipment is necessary for initial configuration and management:

- Dedicated router with internet access
- Mini switch/hub (5 ports) for isolated network setup
- Keyboard and mouse for Raspberry Pi 5 configuration
- Monitor for Raspberry Pi 5 setup
- HDMI cable
- Secondary computer for remote access
- SD-Card Reader/Adapter for imaging the SD card

#### **Optional Equipment**

- SMA cable (included with Nooelec device)
- 3D-printed protective enclosure

---

## **Core Infrastructure Setup (Stage 1)**

### **Network Setup and Initial Configurations**

**Router Configuration:**
1. Connect a management computer (Windows OS) to the router via LAN or Wi-Fi.
2. Set up the router as the DHCP server, configuring the subnet to **192.168.31.0/24** with the router IP as **192.168.31.1**.
3. If using a managed switch, disable DHCP.
4. Ensure internet connectivity for all devices.
5. Verify assigned IP addresses using `ipconfig`.

**Computer Software Setup:**
1. Install PuTTY (or Termius) and RealVNC Viewer.
2. Download and install Raspberry Pi Imager.

### **Imaging the Raspberry Pi OS**

1. Open Raspberry Pi Imager and insert the SD card.
2. Select **Raspberry Pi OS with Desktop**.
3. Write the OS image to the SD card.
4. Remove the SD card and insert it into the Raspberry Pi 5.

### **Starting and Connecting to the Raspberry Pi 5**

1. Connect peripherals (monitor, keyboard, mouse) to the Raspberry Pi 5.
2. Attach a LAN cable and power on the device.
3. Complete the OS setup using the credentials: **Username: falconone, Password: falconone**.

---

## **Raspberry Pi 5 Readiness (Stage 1)**

### **Initial System Setup**

Run the following commands to update the system:
```bash
sudo apt update -y && sudo apt upgrade -y
sudo apt autoremove -y && sudo apt autoclean -y
```

### **Installing Essential Python Packages**

```bash
sudo apt install -y python3 python3-venv python3-pip iotop logrotate
```

---

## **Raspberry Pi 5 and Components Readiness (Stage 2)**

### **Installing RTL-SDR and HackRF Tools**

```bash
sudo apt install -y git build-essential cmake libusb-1.0-0-dev rtl-sdr hackrf
```

Verify hardware detection:
```bash
rtl_test
hackrf_info
```

---

## **Raspberry Pi 5 and Software Readiness (Stage 2)**

### **Installing GNU Radio and GR-GSM**

```bash
sudo apt install -y gnuradio gr-osmosdr gr-gsm
```

Verify installation:
```bash
gnuradio-companion
gqrx
grgsm_livemon -f 950400000
```

### **Installing Kalibrate-RTL**

```bash
git clone https://github.com/steve-m/kalibrate-rtl.git
cd kalibrate-rtl
./bootstrap && ./configure && make && sudo make install
kal -s GSM900
```

---

## **Raspberry Pi 5 and Software Readiness (Stage 3)**

### **TShark Installation and Configuration**

```bash
sudo apt update -y && sudo apt install -y tshark
```

Verify installation:
```bash
tshark --version
```

### **Setting Up Permissions for Non-Root Capture**

```bash
sudo groupadd wireshark
sudo usermod -aG wireshark falconone
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap
```

Verify setup:
```bash
getcap /usr/bin/dumpcap
```

### **Capturing IMSI and SMS Data**

```bash
tshark -i lo -f "udp port 4729" -Y "(e212.imsi or gsm_sms.sms_text)" \
-T fields -e frame.number -e e212.imsi -e gsm_a.tmsi -e gsm_sms.sms_text \
-E header=y -E separator=, -E quote=d
```

This setup ensures IMSI, TMSI, and SMS capture is functional. The FalconOne blueprint is now ready for full deployment.

