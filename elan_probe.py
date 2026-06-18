import sys
import os

# Ensure we can import pyusb from local clone if not installed system-wide
script_dir = os.path.dirname(os.path.abspath(__file__))
pyusb_path = os.path.join(script_dir, 'pyusb')
if os.path.exists(pyusb_path) and pyusb_path not in sys.path:
    sys.path.insert(0, pyusb_path)

import usb.core
import usb.util
import time
import argparse

# Response / Status Code Mapping
RESP_CODES = {
    0x00: "Match Successful (OK)",
    0x41: "Move Down (Too High)",
    0x42: "Move Right (Too Left)",
    0x43: "Move Up (Too Low)",
    0x44: "Move Left (Too Right)",
    0xfb: "Sensor Dirty / Wet",
    0xfd: "Verification Failed (Finger Not Enrolled / No Match)",
    0xfe: "Not Enough Surface Area / Partial Press",
    0xdd: "Max Enrolled Count Reached",
}

def send_cmd(dev, out_data, in_ep, in_len, timeout=1000, silent=False):
    """
    Sends out_data to OUT EP 0x01 and reads in_len bytes from IN EP in_ep.
    """
    out_ep = 0x01
    out_hex = "".join(f" {b:02x}" for b in out_data).strip()
    if not silent:
        print(f"--> Write to EP 0x{out_ep:02x}: [{out_hex}]")
    try:
        dev.write(out_ep, out_data, timeout=timeout)
    except usb.core.USBError as e:
        if not silent:
            print(f"  [ERROR] Write failed: {e}")
        return None

    # Wait a tiny bit for the device to process
    time.sleep(0.01)

    if not silent:
        print(f"<-- Read from EP 0x{in_ep:02x} (expecting {in_len} bytes)...")
    try:
        res = dev.read(in_ep, in_len, timeout=timeout)
        res_hex = "".join(f" {b:02x}" for b in res).strip()
        if not silent:
            print(f"  [SUCCESS] Received: [{res_hex}]")
        return res
    except usb.core.USBError as e:
        if e.errno == 110 or "timeout" in str(e).lower():
            if not silent:
                print(f"  [TIMEOUT] No response received within {timeout}ms")
        else:
            if not silent:
                print(f"  [ERROR] Read failed: {e}")
        return None

def probe_device(mode="info"):
    VENDOR_ID = 0x04f3
    PRODUCT_ID = 0x0c00
    INTERFACE_NUM = 0

    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

    if dev is None:
        print("Device not found. Please ensure it is plugged in.")
        return

    # Detach kernel driver if active
    try:
        if dev.is_kernel_driver_active(INTERFACE_NUM):
            dev.detach_kernel_driver(INTERFACE_NUM)
    except NotImplementedError:
        pass
    except usb.core.USBError as e:
        pass

    # Claim interface
    try:
        usb.util.claim_interface(dev, INTERFACE_NUM)
    except usb.core.USBError as e:
        print(f"Failed to claim interface {INTERFACE_NUM}: {e}")
        print("Please run the script with 'sudo'.")
        return

    try:
        # Check calibration status first to verify if device is ready
        status = send_cmd(dev, [0x40, 0xff, 0x00], in_ep=0x83, in_len=2, silent=True)
        if status is None or len(status) < 2 or status[1] != 0x03:
            print("Warning: Sensor reports it is not fully ready/calibrated.")
        else:
            print("Sensor status: Calibrated & Ready.")

        # Read enrolled finger count
        count_res = send_cmd(dev, [0x40, 0xff, 0x04], in_ep=0x83, in_len=2, silent=True)
        enrolled_count = 0
        if count_res is not None and len(count_res) >= 2:
            enrolled_count = count_res[1]
            print(f"Enrolled Fingerprints on Chip: {enrolled_count}")

        if mode == "info":
            # Let's query all finger indices (0 to 9) to see where the fingerprints are stored
            print("\nQuerying Finger Info database (indices 0-9):")
            active_indices = []
            for idx in range(10):
                res = send_cmd(dev, [0x40, 0xff, 0x12, idx], in_ep=0x83, in_len=64, silent=True)
                if res is not None and len(res) >= 2:
                    if res[1] == 0xff:
                        # Index is empty
                        pass
                    else:
                        # Index contains data, print label if any
                        label_bytes = res[2:]
                        label = "".join(chr(b) for b in label_bytes if 32 <= b < 127).strip()
                        print(f"  * Finger Index {idx}: Active! Label/ID: '{label}'")
                        active_indices.append(idx)
                else:
                    print(f"  * Finger Index {idx}: No response or read error")
            
            if not active_indices and enrolled_count > 0:
                print("\nNotice: Enrolled count is greater than 0, but no active indices returned info.")
                print("This is normal for some firmware versions where the ID label is null.")
                
            print("\nTo test finger placement and verification, run:")
            print("  sudo python3 elan_probe.py --verify")

        elif mode == "verify":
            print("\n=== STARTING VERIFICATION TEST ===")
            print("Initializing & Calibrating sensor... Keep your finger OFF the sensor.")
            time.sleep(2.0)
            
            print("\n>>> SENSOR READY! Place your enrolled finger on the sensor NOW. <<<")
            print("Waiting up to 15 seconds for finger press...\n")

            start_time = time.time()
            timeout_limit = 15.0
            
            while True:
                # Check overall timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout_limit:
                    print("\n[TIMEOUT] No successful match within 15 seconds. Cancelling...")
                    # Send abort command to reset the sensor state
                    send_cmd(dev, [0x40, 0xff, 0x02], in_ep=0x83, in_len=2, silent=True)
                    break
                
                # Send Identify Command (0xff 0x03)
                send_cmd(dev, [0x40, 0xff, 0x03], in_ep=0x83, in_len=2, silent=True)
                
                # Read from EP 0x84 (MOC Channel)
                rem_timeout = int((timeout_limit - elapsed) * 1000)
                if rem_timeout <= 0:
                    break
                try:
                    res = dev.read(0x84, 2, timeout=rem_timeout)
                    if len(res) >= 2:
                        status_code = res[1]
                        
                        if status_code < 10:  # SUCCESS (Finger Index matched)
                            print("------------------------------------------")
                            print(f"  SUCCESS: Finger matched! Matched Index: {status_code}")
                            print("------------------------------------------")
                            break
                        
                        elif status_code == 0xfd:  # NO MATCH
                            print("------------------------------------------")
                            print("  RESULT: Verification Failed (Finger Not Enrolled / No Match)")
                            print("------------------------------------------")
                            break
                            
                        elif status_code in RESP_CODES:
                            # Transient status (dirty, partial press, move directions), print and retry
                            print(f"  [Status Warning] {RESP_CODES[status_code]}. Retrying scan...")
                            time.sleep(0.5)  # Small delay before retrying command
                            
                        else:
                            print(f"  [Unknown status] Code: 0x{status_code:02x}. Retrying...")
                            time.sleep(0.5)
                    else:
                        print("Received empty response. Retrying...")
                        time.sleep(0.5)
                except usb.core.USBError as e:
                    if e.errno == 110 or "timeout" in str(e).lower():
                        # Timeout on read means no touch yet, retry command after a tiny sleep
                        time.sleep(0.2)
                    else:
                        print(f"MOC Read Error: {e}")
                        break

    finally:
        try:
            usb.util.release_interface(dev, INTERFACE_NUM)
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Elan Fingerprint Sensor Command Prober")
    parser.add_argument("--verify", action="store_true", help="Run finger verification test")
    args = parser.parse_args()

    mode = "verify" if args.verify else "info"
    probe_device(mode=mode)
