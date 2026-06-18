# Elan 04f3:0c00 Fingerprint Sensor - Linux Guide & Probe Tools

This repository provides a complete, step-by-step guide to compiling and installing the community-developed `elanmoc2` driver for the unsupported Elan Match-on-Chip fingerprint sensor (USB ID `04f3:0c00`) on Ubuntu/Debian-based distributions.

It also includes a Python USB probing script for those interested in exploring the hardware communication protocol.

---

## Prerequisites & Verification

First, verify that your fingerprint reader is indeed the supported Elan Match-on-Chip model:
```bash
lsusb | grep -i elan
```
You should see an output containing the hardware ID:
`Bus XXX Device YYY: ID 04f3:0c00 Elan Microelectronics Corp. ELAN:ARM-M4`

---

## Step 1: Install Build Dependencies

Before compiling, you need to install the required compilers and development libraries. On Ubuntu/Debian-based distributions (like Linux Mint), run the following command:
```bash
sudo apt-get update
sudo apt-get install -y \
  meson \
  ninja-build \
  libglib2.0-dev \
  libgusb-dev \
  libnss3-dev \
  libpixman-1-dev \
  libcairo2-dev \
  libgirepository1.0-dev \
  libssl-dev \
  libgudev-1.0-dev \
  gobject-introspection
```

---

## Step 2: Clone the Driver Repository

Clone the specific community branch (`elanmoc2`) of the `libfprint` fork maintained by Davide Depau:
```bash
git clone --depth 1 -b elanmoc2 https://gitlab.freedesktop.org/depau/libfprint.git
cd libfprint
```

---

## Step 3: Configure the Build

Configure the build directory using `meson`. We disable the API documentation (`-Ddoc=false`) to avoid extra dependency requirements (like `gtk-doc`):
```bash
meson setup builddir -Ddoc=false
```

---

## Step 4: Compile and Install

Build the library and install it onto the system:
```bash
# Compile the library
ninja -C builddir

# Install to the default system paths
sudo ninja -C builddir install
```

---

## Step 5: Post-Installation Setup

1. **Update Dynamic Linker Bindings:** Ensure that the newly installed library under `/usr/local/lib/x86_64-linux-gnu` is cached and preferred by the dynamic linker:
   ```bash
   sudo ldconfig
   ```

2. **Restart the Fingerprint Service:** Restart the `fprintd` system daemon so it loads the newly installed driver:
   ```bash
   sudo systemctl restart fprintd
   ```

---

## Step 6: Enroll Your Fingerprint

Run the enrollment utility to register your fingerprint:
```bash
fprintd-enroll -f right-index-finger
```

### 💡 Crucial Enrollment Tip:
* When the utility starts, place your finger on the sensor.
* As soon as you see `Enroll result: enroll-stage-passed`, lift your finger completely off the sensor and wait a moment.
* Place your finger back on the sensor (preferably at a slightly different angle to scan the sides).
* Repeat this **"touch → lift → touch"** sequence until all enrollment stages complete.
* Keeping your finger pressed continuously on the sensor will cause it to timeout with `enroll-remove-and-retry` warnings.

---

## 🛠️ Hardware Reverse Engineering & Probing

For developers interested in the underlying protocol, this repository includes `elan_probe.py`. This script utilizes `pyusb` to claim the device interface, detach any active kernel drivers, and probe the IN/OUT endpoints (`0x81-0x84`, `0x01-0x04`) of the ARM-M4 chip.

### Probing Script Overview
The script performs the following core actions:
1. Locates the device `04f3:0c00`.
2. Detaches any kernel driver and claims Interface 0.
3. Performs a ready/calibration check (`[0x40, 0xff, 0x00]`).
4. Queries enrolled count (`[0x40, 0xff, 0x04]`).
5. Queries metadata for finger indices `0-9` (`[0x40, 0xff, 0x12, index]`).
6. Enters a MOC identify loop: sends `[0x40, 0xff, 0x03]` and reads from endpoint `0x84` to detect finger press and report the matched finger index or warnings (e.g. dirty, partial press).

### Running the Probe:
```bash
sudo python3 elan_probe.py
```
*(Note: Root privileges are required to claim the USB interface without specific udev rules).*

---

## Acknowledgments
All credit for the `elanmoc2` driver code goes to Davide Depau and the `libfprint` community.
