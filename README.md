```markdown
# Elan 04f3:0c00 Fingerprint Sensor - Complete Ubuntu Setup Guide

This guide provides the complete, step-by-step process to compile, install, and enable the community-developed `elanmoc2` driver for the unsupported Elan Match-on-Chip fingerprint sensor (`04f3:0c00`) on Ubuntu 25.10 and 26.04 LTS. It includes the crucial PAM authentication steps and build-cleanup instructions.

## Prerequisites & Verification

First, verify that your fingerprint reader is the supported Elan Match-on-Chip model:

```bash
lsusb | grep -i elan

```

*Expected Output:* `Bus XXX Device YYY: ID 04f3:0c00 Elan Microelectronics Corp. ELAN:ARM-M4`

---

## Step 1: Install Authentication Stack & Build Dependencies

You need both the base Ubuntu fingerprint daemon tools and the development libraries required to compile the custom driver.

```bash
sudo apt-get update
sudo apt-get install -y \
  fprintd \
  libpam-fprintd \
  meson \
  ninja-build \
  libglib2.0-dev \
  libgusb-dev \
  libnss3-dev \
  libpixman-1-dev \
  libcairo2-dev \
  libgirepository1.0-dev \
  libssl-dev \
  libudev-dev \
  systemd-dev \
  libgudev-1.0-dev \
  gobject-introspection

```

---

## Step 2: Clone the Driver Repository

Clone the specific community branch (`elanmoc2`) of the `libfprint` fork maintained by Davide Depau.

```bash
git clone --depth 1 -b elanmoc2 https://gitlab.freedesktop.org/depau/libfprint.git
cd libfprint

```

---

## Step 3: Configure, Compile, and Install

1. **Configure the build directory** (disabling API documentation to avoid extra dependencies):
```bash
meson setup builddir -Ddoc=false

```


2. **Compile the library**:
```bash
ninja -C builddir

```


3. **Install the driver** onto the system:
```bash
sudo ninja -C builddir install

```



---

## Step 4: System Binding & Service Restart

Ensure your OS recognizes the newly installed library and loads it into the active authentication daemon.

1. **Update Dynamic Linker Bindings:**
```bash
sudo ldconfig

```


2. **Restart the Fingerprint Service:**
```bash
sudo systemctl restart fprintd

```



---

## Step 5: Enroll Your Fingerprint

Run the enrollment utility to register your fingerprint:

```bash
fprintd-enroll -f right-index-finger

```

> **⚠️ CRUCIAL ENROLLMENT TIP:**
> When the utility starts, place your finger on the sensor. As soon as you see `Enroll result: enroll-stage-passed`, **lift your finger completely off the sensor**. Place your finger back on the sensor at a slightly different angle.
> Repeat this **"touch → lift → touch"** sequence until all stages complete. Keeping your finger pressed continuously will cause the hardware firmware to time out and fail.

## Step 5.1: Enroll any other Fingerprints

Run the enrollment utility to register another fingerprint, below I show how to enroll the left finger fingerprints:

```bash
fprintd-enroll -f left-index-finger

```

---

## Step 6: Enable Fingerprint Authentication (PAM)

This is the critical step to ensure your fingerprint can actually be used at the GNOME login screen and for `sudo` terminal commands.

1. Run the Pluggable Authentication Modules (PAM) configuration tool:
```bash
sudo pam-auth-update

```


2. A graphical text menu will appear. Use the **Up/Down arrows** to navigate.
3. Ensure the **Fingerprint authentication** profile has an asterisk **`[*]`** next to it. (Press the `Spacebar` to toggle it on if it is empty).
4. Press `Tab` to highlight `<Ok>` and press `Enter`.

*You can now lock your screen (`Super` + `L`) or open a new terminal and run a `sudo` command to test the scanner.*

---

## Step 7: Clean Up Build Environment (Optional)

To keep your host OS pristine, you can safely remove the compilers and development headers now that the driver is permanently installed in `/usr/local/lib/`.

```bash
sudo apt-get autoremove --purge \
  meson ninja-build libglib2.0-dev libgusb-dev \
  libnss3-dev libpixman-1-dev libcairo2-dev \
  libgirepository1.0-dev libssl-dev \
  libudev-dev systemd-dev \
  libgudev-1.0-dev gobject-introspection

```

---

## Bonus: Hardware Reverse Engineering & Probing

If you are interested in hardware communication protocols, you can use the `elan_probe.py` script included in the `gianniskokkinis` guide repo.

This script utilizes `pyusb` to claim the device interface and probe the IN/OUT endpoints (`0x81-0x84`, `0x01-0x04`) of the ARM-M4 chip.

**Running the Probe:**

```bash
sudo python3 elan_probe.py

```

*Note: This performs a calibration check, queries enrolled count, queries metadata for finger indices, and detects partial/dirty presses directly from the hardware.*

```

```
