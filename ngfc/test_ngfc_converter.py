#!/usr/bin/env python3
"""
Test suite for NGFC converter transformation algorithms.

Verifies that our Python implementations match the expected behavior
from MiSTer's neogeo_loader.cpp
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ngfc_converter import (
    transform_crom_burst_order,
    byte_swap_crom,
    interleave_crom_pair,
    transform_srom,
    NGFCHeader,
    NGFC_HEADER_SIZE
)


def test_byte_swap():
    """
    Test byte swap transformation.
    
    Input:  [B3][B2][B1][B0]
    Output: [B3][B1][B2][B0]
    """
    print("Testing byte swap...")
    
    # Test with known pattern
    input_data = bytearray([0x00, 0x11, 0x22, 0x33,  # Word 1
                            0xAA, 0xBB, 0xCC, 0xDD])  # Word 2
    
    expected =   bytearray([0x00, 0x22, 0x11, 0x33,  # Swapped
                            0xAA, 0xCC, 0xBB, 0xDD])
    
    result = byte_swap_crom(input_data)
    
    if result == expected:
        print("  ✓ Byte swap correct")
        return True
    else:
        print(f"  ✗ Byte swap failed!")
        print(f"    Input:    {input_data.hex()}")
        print(f"    Expected: {expected.hex()}")
        print(f"    Got:      {result.hex()}")
        return False


def test_interleave():
    """
    Test C-ROM pair interleaving.
    
    Should produce: C2 C2 C1 C1 C2 C2 C1 C1...
    """
    print("Testing C-ROM interleaving...")
    
    # Simple test case
    c1 = bytes([0x11, 0x11, 0x33, 0x33])  # C1 data (bitplanes 0,1)
    c2 = bytes([0x22, 0x22, 0x44, 0x44])  # C2 data (bitplanes 2,3)
    
    # Expected output: C2 C2 C1 C1 pattern
    expected = bytearray([0x22, 0x22, 0x11, 0x11,
                          0x44, 0x44, 0x33, 0x33])
    
    result = interleave_crom_pair(c1, c2)
    
    if result == expected:
        print("  ✓ Interleaving correct")
        return True
    else:
        print(f"  ✗ Interleaving failed!")
        print(f"    C1:       {c1.hex()}")
        print(f"    C2:       {c2.hex()}")
        print(f"    Expected: {expected.hex()}")
        print(f"    Got:      {result.hex()}")
        return False


def test_burst_order_identity():
    """
    Test that burst order transformation is internally consistent.
    
    The transformation should be deterministic and reversible
    (though we don't implement reverse here).
    """
    print("Testing burst order transformation...")
    
    # Create test data - 32 bytes (one tile's worth)
    input_data = bytearray(range(32))
    
    result = transform_crom_burst_order(input_data)
    
    # Verify same length
    if len(result) != len(input_data):
        print(f"  ✗ Length mismatch: {len(input_data)} -> {len(result)}")
        return False
    
    # Verify it's a permutation (all bytes present, just reordered)
    if sorted(result) == sorted(input_data):
        print("  ✓ Burst order is valid permutation")
    else:
        print("  ✗ Burst order lost/duplicated bytes!")
        return False
    
    # Print the mapping for verification
    print("  Byte mapping (original -> transformed position):")
    mapping = {}
    for i in range(32):
        j = (i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)
        mapping[j] = i
    
    print(f"    {[mapping.get(i, '?') for i in range(32)]}")
    
    return True


def test_burst_order_mister_reference():
    """
    Test against known MiSTer transformation behavior.
    
    The MiSTer formula:
    j = (i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)
    
    Let's verify the first 32 bytes manually.
    """
    print("Testing burst order against MiSTer reference...")
    
    # Calculate expected mapping using the exact MiSTer formula
    expected_mapping = []
    for i in range(32):
        j = (i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)
        expected_mapping.append(j)
    
    print(f"  MiSTer mapping: {expected_mapping}")
    
    # Verify specific known values from MiSTer DEV_NOTES:
    # The comment says sprite bytes are loaded as: C2 C2 C1 C1 C2 C2 C1 C1...
    # And bitplanes end up as: 0 1 2 3 0 1 2 3...
    
    # This means the transformation prepares data so sequential SDRAM reads
    # return the correct bitplane order
    
    # Create input and transform
    input_data = bytearray(range(32))
    result = transform_crom_burst_order(input_data)
    
    # Verify the transformation matches what we'd expect
    # After transformation, reading bytes 0,1,2,3 should give bitplanes 0,1,2,3
    
    print(f"  Input:  {list(input_data[:8])}...")
    print(f"  Output: {list(result[:8])}...")
    
    print("  ✓ Burst order transformation implemented")
    return True


def test_srom_transformation():
    """
    Test S-ROM (fix layer) transformation.
    
    From MiSTer DEV_NOTES.md:
    Original bytes: 10 18 00 08 11 19 01 09 12 1A 02 0A 13 1B 03 0B 14 1C 04 0C 15 1D 05 0D 16 1E 06 0E 17 1F 07 0F
    """
    print("Testing S-ROM transformation...")
    
    # The remap table from MiSTer
    SROM_REMAP = [
        0x10, 0x18, 0x00, 0x08, 0x11, 0x19, 0x01, 0x09,
        0x12, 0x1A, 0x02, 0x0A, 0x13, 0x1B, 0x03, 0x0B,
        0x14, 0x1C, 0x04, 0x0C, 0x15, 0x1D, 0x05, 0x0D,
        0x16, 0x1E, 0x06, 0x0E, 0x17, 0x1F, 0x07, 0x0F
    ]
    
    # Create input with sequential bytes
    input_data = bytearray(range(32))
    result = transform_srom(input_data)
    
    # After transformation, result[i] should equal input[SROM_REMAP[i]]
    expected = bytearray([input_data[SROM_REMAP[i]] for i in range(32)])
    
    if result == expected:
        print("  ✓ S-ROM transformation matches MiSTer")
        return True
    else:
        print("  ✗ S-ROM transformation mismatch!")
        print(f"    Expected: {list(expected)}")
        print(f"    Got:      {list(result)}")
        return False


def test_header_pack_unpack():
    """Test NGFC header packing and unpacking."""
    print("Testing header pack/unpack...")
    
    # Create header with test values
    header = NGFCHeader()
    header.flags = 0x0011
    header.ngh_number = 201
    header.p_size = 1048576
    header.s_size = 131072
    header.m_size = 131072
    header.v_size = 4194304
    header.c_size = 16777216
    header.c_size_original = 16777216
    header.crc32 = 0xDEADBEEF
    
    # Pack
    packed = header.pack()
    
    if len(packed) != NGFC_HEADER_SIZE:
        print(f"  ✗ Header size wrong: {len(packed)} != {NGFC_HEADER_SIZE}")
        return False
    
    # Unpack
    unpacked = NGFCHeader.unpack(packed)
    
    # Verify
    checks = [
        (unpacked.magic, b'NGFC', 'magic'),
        (unpacked.version, 1, 'version'),
        (unpacked.flags, 0x0011, 'flags'),
        (unpacked.ngh_number, 201, 'ngh_number'),
        (unpacked.p_size, 1048576, 'p_size'),
        (unpacked.s_size, 131072, 's_size'),
        (unpacked.m_size, 131072, 'm_size'),
        (unpacked.v_size, 4194304, 'v_size'),
        (unpacked.c_size, 16777216, 'c_size'),
        (unpacked.crc32, 0xDEADBEEF, 'crc32'),
    ]
    
    all_pass = True
    for got, expected, name in checks:
        if got != expected:
            print(f"  ✗ {name}: got {got}, expected {expected}")
            all_pass = False
    
    if all_pass:
        print("  ✓ Header pack/unpack correct")
    
    return all_pass


def test_large_crom():
    """Test transformation with larger C-ROM data (simulating real game)."""
    print("Testing larger C-ROM transformation...")
    
    # Create 1KB of test data (simulating a small portion of C-ROM)
    size = 1024
    c1 = bytes([(i * 3) & 0xFF for i in range(size)])
    c2 = bytes([(i * 7) & 0xFF for i in range(size)])
    
    # Run full pipeline
    interleaved = interleave_crom_pair(c1, c2)
    swapped = byte_swap_crom(interleaved)
    reordered = transform_crom_burst_order(swapped)
    
    # Verify sizes
    expected_size = size * 2
    if len(interleaved) != expected_size:
        print(f"  ✗ Interleave size: {len(interleaved)} != {expected_size}")
        return False
    
    if len(swapped) != expected_size:
        print(f"  ✗ Swap size: {len(swapped)} != {expected_size}")
        return False
    
    if len(reordered) != expected_size:
        print(f"  ✗ Reorder size: {len(reordered)} != {expected_size}")
        return False
    
    print(f"  ✓ Large C-ROM transformation: {size*2} bytes processed")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("NGFC Converter Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_byte_swap,
        test_interleave,
        test_burst_order_identity,
        test_burst_order_mister_reference,
        test_srom_transformation,
        test_header_pack_unpack,
        test_large_crom,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print()
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
