"""
Quick test: polls the two candidate characteristics and prints both values side by side.
Breathe deeply for 15 seconds and watch which one oscillates.
"""

import asyncio
import struct
from bleak import BleakScanner, BleakClient

# The two candidates
CANDIDATE_A = "248d6f39-5819-11e6-8b77-86f30ca893d3"   # int=7500 — likely breathing
CANDIDATE_B = "8e6f094a-5819-11e6-8b77-86f30ca893d3"   # int=309M  — likely timestamp

async def main():
    print("Scanning for GDX-RB...")
    devices = await BleakScanner.discover(timeout=10.0)
    belt = next((d for d in devices if "GDX-RB" in str(d.name)), None)
    if not belt:
        raise Exception("GDX-RB not found")
    print(f"Found {belt.name} at {belt.address}")

    async with BleakClient(belt.address) as client:
        print("✓ Connected!\n")
        print("Breathe IN and OUT deeply for 15 seconds...\n")
        print(f"{'#':>4}  {'Char A (7500-range)':>22}  {'Char B (300M-range)':>22}")
        print("-" * 55)

        a_vals = []
        b_vals = []

        for i in range(150):  # 15 seconds at 10 Hz
            try:
                data_a = await client.read_gatt_char(CANDIDATE_A)
                val_a  = struct.unpack('<i', data_a[:4])[0] if len(data_a) >= 4 else 0
            except Exception:
                val_a = -1

            try:
                data_b = await client.read_gatt_char(CANDIDATE_B)
                val_b  = struct.unpack('<i', data_b[:4])[0] if len(data_b) >= 4 else 0
            except Exception:
                val_b = -1

            a_vals.append(val_a)
            b_vals.append(val_b)
            print(f"[{i:3d}]  {val_a:>22,}  {val_b:>22,}")
            await asyncio.sleep(0.1)

        print("\n" + "=" * 55)
        print("RESULTS:")
        for label, vals in [("Char A (248d...)", a_vals), ("Char B (8e6f...)", b_vals)]:
            if vals:
                rng = max(vals) - min(vals)
                print(f"  {label}:  min={min(vals):,}  max={max(vals):,}  range={rng:,}")
                if rng > 500:
                    print(f"    *** THIS ONE VARIES WITH BREATHING — use this UUID ***")
                else:
                    print(f"    → Flat, not the breathing signal")

if __name__ == "__main__":
    asyncio.run(main())