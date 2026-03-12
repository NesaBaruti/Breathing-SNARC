"""
STEP 1: Run this first to discover ALL characteristics on the GDX-RB belt.
This will help identify which characteristic carries the actual breathing signal.
"""

import asyncio
import struct
import time
from bleak import BleakScanner, BleakClient

async def discover_all_characteristics():
    print("Scanning for GDX-RB...")
    devices = await BleakScanner.discover(timeout=10.0)

    belt = None
    for d in devices:
        if "GDX-RB" in str(d.name):
            belt = d
            print(f"Found: {d.name} at {d.address}")
            break

    if not belt:
        raise Exception("GDX-RB not found")

    async with BleakClient(belt.address) as client:
        print(f"\n✓ Connected!\n")
        print("=" * 70)
        print("ALL SERVICES AND CHARACTERISTICS:")
        print("=" * 70)

        notify_chars = []

        for service in client.services:
            print(f"\n[SERVICE] {service.uuid}  —  {service.description}")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"  [CHAR]  {char.uuid}  |  Props: {props}")

                # Try to read readable characteristics
                if "read" in char.properties:
                    try:
                        data = await client.read_gatt_char(char.uuid)
                        raw_hex = data.hex()
                        bytes_list = list(data)

                        # Try to parse as int
                        val_int = None
                        if len(data) >= 4:
                            val_int = struct.unpack('<i', data[:4])[0]

                        print(f"          ↳ READ: hex={raw_hex} | int={val_int} | bytes={bytes_list}")
                    except Exception as e:
                        print(f"          ↳ READ failed: {e}")

                # Collect notify-capable characteristics for next step
                if "notify" in char.properties:
                    notify_chars.append(char.uuid)
                    print(f"          ↳ *** NOTIFY CAPABLE — will test this ***")

        print("\n" + "=" * 70)
        print(f"\nNOTIFY-CAPABLE characteristics found: {len(notify_chars)}")
        for uuid in notify_chars:
            print(f"  {uuid}")

        if not notify_chars:
            print("\nNo notify characteristics found. Will test polling on all readable chars.")
            return

        # Now test each notify characteristic for 5 seconds
        print("\n" + "=" * 70)
        print("TESTING NOTIFY CHARACTERISTICS (5 seconds each):")
        print("Breathe deeply while watching for oscillating values!")
        print("=" * 70)

        for uuid in notify_chars:
            print(f"\n[TESTING] {uuid}")
            print("Breathe IN and OUT deeply now...")

            samples = []

            def handler(sender, data):
                raw_hex = data.hex()
                bytes_list = list(data)
                val_int = struct.unpack('<i', data[:4])[0] if len(data) >= 4 else None
                val_float = struct.unpack('<f', data[:4])[0] if len(data) >= 4 else None
                val_int32_b3 = None
                # Try reading bytes 2-5 (offset by 2) as int
                if len(data) >= 6:
                    val_int32_b3 = struct.unpack('<i', data[2:6])[0]

                sample_str = (f"  hex={raw_hex} | int={val_int} | float={val_float:.3f}"
                              f" | int@2={val_int32_b3} | bytes={bytes_list}")
                print(sample_str)
                samples.append(val_int)

            try:
                await client.start_notify(uuid, handler)
                await asyncio.sleep(5)
                await client.stop_notify(uuid)

                if samples and len(samples) > 3:
                    mn, mx = min(samples), max(samples)
                    rng = mx - mn
                    print(f"  → Range: {mn} to {mx}  (spread: {rng})")
                    if rng > 1000:
                        print(f"  *** THIS CHARACTERISTIC SHOWS VARIATION — LIKELY THE BREATHING SIGNAL! ***")
                    elif rng == 0:
                        print(f"  → No variation detected (probably not the signal)")
                    else:
                        print(f"  → Small variation, might need more breathing effort")

            except Exception as e:
                print(f"  → Notify failed: {e}")


if __name__ == "__main__":
    asyncio.run(discover_all_characteristics())