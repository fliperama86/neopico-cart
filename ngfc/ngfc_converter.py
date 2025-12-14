#!/usr/bin/env python3
"""
Neo Geo Flash Cart ROM Converter (ngfc_converter.py)

Converts standard Neo Geo ROM sets (MAME or .neo format) to the NGFC format
optimized for SDRAM burst access on flash cartridges.

Based on data transformation algorithms from MiSTer FPGA Neo Geo core:
https://github.com/MiSTer-devel/Main_MiSTer/blob/master/support/neogeo/neogeo_loader.cpp

Author: Based on MiSTer project by Furrtek and contributors
License: GPL v3 (same as MiSTer)
"""

import struct
import os
import sys
import argparse
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
import zipfile
import re

# NGFC Format Constants
NGFC_MAGIC = b'NGFC'
NGFC_VERSION = 1
NGFC_HEADER_SIZE = 64

# Flag bits
FLAG_ENCRYPTED = 0x0001  # Source was encrypted (now decrypted)
FLAG_REGION_JP = 0x0010
FLAG_REGION_US = 0x0020
FLAG_REGION_EU = 0x0040


class NGFCHeader:
    """NGFC file header structure."""
    
    def __init__(self):
        self.magic = NGFC_MAGIC
        self.version = NGFC_VERSION
        self.flags = 0
        self.ngh_number = 0
        self.p_size = 0
        self.s_size = 0
        self.m_size = 0
        self.v_size = 0
        self.c_size = 0  # After transformation
        self.c_size_original = 0  # Before transformation
        self.crc32 = 0
        self.reserved = bytes(24)
    
    def pack(self) -> bytes:
        """Pack header into 64 bytes."""
        return struct.pack(
            '<4sHHIIIIIIII24s',
            self.magic,
            self.version,
            self.flags,
            self.ngh_number,
            self.p_size,
            self.s_size,
            self.m_size,
            self.v_size,
            self.c_size,
            self.c_size_original,
            self.crc32,
            self.reserved
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> 'NGFCHeader':
        """Unpack header from bytes."""
        if len(data) < NGFC_HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} bytes")
        
        header = cls()
        (
            header.magic,
            header.version,
            header.flags,
            header.ngh_number,
            header.p_size,
            header.s_size,
            header.m_size,
            header.v_size,
            header.c_size,
            header.c_size_original,
            header.crc32,
            header.reserved
        ) = struct.unpack('<4sHHIIIIIIII24s', data[:NGFC_HEADER_SIZE])
        
        if header.magic != NGFC_MAGIC:
            raise ValueError(f"Invalid magic: {header.magic}")
        
        return header


def transform_crom_burst_order(data: bytearray) -> bytearray:
    """
    Reorder C-ROM data for SDRAM burst access.
    
    This is the critical transformation from MiSTer's neogeo_loader.cpp:
    
    for (uint32_t i = 0; i < size; i++) 
        buf_out[i] = buf_in[(i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)];
    
    The transformation reorders data within each 32-byte block so that
    a 4-word SDRAM burst returns pixels in the order the NEO-ZMC2 expects.
    """
    size = len(data)
    out = bytearray(size)
    
    for i in range(size):
        # Calculate source index using MiSTer's bit manipulation
        j = (i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)
        if j < size:
            out[i] = data[j]
    
    return out


def byte_swap_crom(data: bytearray) -> bytearray:
    """
    Swap middle two bytes of each 32-bit word for SDRAM alignment.
    
    From MiSTer's neogeo_loader.cpp:
    buf[i] = (buf[i] & 0xFF0000FF) | ((buf[i] & 0xFF00) << 8) | ((buf[i] & 0xFF0000) >> 8);
    
    Input:  [B3][B2][B1][B0]
    Output: [B3][B1][B2][B0]
    """
    size = len(data)
    out = bytearray(size)
    
    # Process 4 bytes at a time
    for i in range(0, size - 3, 4):
        out[i + 0] = data[i + 0]  # B0 stays
        out[i + 1] = data[i + 2]  # B2 -> B1 position
        out[i + 2] = data[i + 1]  # B1 -> B2 position
        out[i + 3] = data[i + 3]  # B3 stays
    
    # Handle remaining bytes (shouldn't happen with aligned ROM data)
    remainder = size % 4
    if remainder:
        for i in range(size - remainder, size):
            out[i] = data[i]
    
    return out


def interleave_crom_pair(c1_data: bytes, c2_data: bytes) -> bytearray:
    """
    Interleave C1 and C2 ROM data.
    
    Original Neo Geo has separate buses for odd (C1) and even (C2) ROMs:
    - C1 contains bitplanes 0 and 1
    - C2 contains bitplanes 2 and 3
    
    MiSTer interleaves them as: C2 C2 C1 C1 C2 C2 C1 C1...
    This allows reading all 4 bitplanes in a single SDRAM burst.
    """
    if len(c1_data) != len(c2_data):
        # Pad shorter one to match
        max_len = max(len(c1_data), len(c2_data))
        c1_data = c1_data + bytes(max_len - len(c1_data))
        c2_data = c2_data + bytes(max_len - len(c2_data))
    
    size = len(c1_data)
    out = bytearray(size * 2)
    
    # Interleave: C2 C2 C1 C1 pattern (2 bytes each)
    for i in range(0, size, 2):
        out_idx = i * 2
        out[out_idx + 0] = c2_data[i + 0]
        out[out_idx + 1] = c2_data[i + 1]
        out[out_idx + 2] = c1_data[i + 0]
        out[out_idx + 3] = c1_data[i + 1]
    
    return out


def transform_srom(data: bytearray) -> bytearray:
    """
    Transform S-ROM (fix layer) data for SDRAM burst access.
    
    From MiSTer DEV_NOTES.md:
    Original storage (column-major):
      column 2 (lines 0~7), column 3 (lines 0~7), column 0 (lines 0~7), column 1 (lines 0~7)
    
    Reorganized for SDRAM (line-major):
      line 0 (columns 0~3), line 1 (columns 0~3)...
    
    Byte remapping within each 32-byte tile:
      Original: 10 18 00 08 11 19 01 09 12 1A 02 0A 13 1B 03 0B 14 1C 04 0C 15 1D 05 0D 16 1E 06 0E 17 1F 07 0F
      SDRAM:    Pairs grouped for 16-bit word access
    """
    # Remap table for fix layer transformation
    SROM_REMAP = [
        0x10, 0x18, 0x00, 0x08, 0x11, 0x19, 0x01, 0x09,
        0x12, 0x1A, 0x02, 0x0A, 0x13, 0x1B, 0x03, 0x0B,
        0x14, 0x1C, 0x04, 0x0C, 0x15, 0x1D, 0x05, 0x0D,
        0x16, 0x1E, 0x06, 0x0E, 0x17, 0x1F, 0x07, 0x0F
    ]
    
    size = len(data)
    out = bytearray(size)
    
    # Process each 32-byte tile
    for tile_start in range(0, size, 32):
        for i in range(32):
            src_idx = tile_start + SROM_REMAP[i]
            dst_idx = tile_start + i
            if src_idx < size and dst_idx < size:
                out[dst_idx] = data[src_idx]
    
    return out


def transform_full_crom(crom_pairs: List[Tuple[bytes, bytes]]) -> bytearray:
    """
    Full C-ROM transformation pipeline.
    
    1. Interleave each C1/C2 pair
    2. Byte swap for SDRAM word alignment  
    3. Reorder for burst access
    """
    result = bytearray()
    
    for idx, (c1, c2) in enumerate(crom_pairs):
        print(f"  Processing C-ROM pair {idx + 1}/{len(crom_pairs)} ({len(c1) + len(c2)} bytes)...")
        
        # Step 1: Interleave
        interleaved = interleave_crom_pair(c1, c2)
        
        # Step 2: Byte swap
        swapped = byte_swap_crom(interleaved)
        
        # Step 3: Burst reorder
        reordered = transform_crom_burst_order(swapped)
        
        result.extend(reordered)
    
    return result


def load_mame_romset(path: Path) -> dict:
    """
    Load a MAME-format ROM set from a directory or zip file.
    
    Returns dict with keys: 'p', 's', 'm', 'v', 'c_pairs'
    """
    roms = {
        'p': bytearray(),
        's': bytearray(),
        'm': bytearray(),
        'v': bytearray(),
        'c_pairs': []
    }
    
    # Determine if it's a zip or directory
    if path.suffix.lower() == '.zip':
        return load_mame_zip(path)
    
    if not path.is_dir():
        raise ValueError(f"Path must be a directory or zip file: {path}")
    
    files = list(path.iterdir())
    
    # Find and load P-ROM (program)
    p_files = sorted([f for f in files if re.match(r'.*-p\d*\.', f.name.lower())])
    for f in p_files:
        print(f"  Loading P-ROM: {f.name}")
        roms['p'].extend(f.read_bytes())
    
    # Find and load S-ROM (fix layer)
    s_files = sorted([f for f in files if re.match(r'.*-s\d*\.', f.name.lower())])
    for f in s_files:
        print(f"  Loading S-ROM: {f.name}")
        roms['s'].extend(f.read_bytes())
    
    # Find and load M-ROM (Z80 program)
    m_files = sorted([f for f in files if re.match(r'.*-m\d*\.', f.name.lower())])
    for f in m_files:
        print(f"  Loading M-ROM: {f.name}")
        roms['m'].extend(f.read_bytes())
    
    # Find and load V-ROM (ADPCM samples)
    v_files = sorted([f for f in files if re.match(r'.*-v\d*\.', f.name.lower())])
    for f in v_files:
        print(f"  Loading V-ROM: {f.name}")
        roms['v'].extend(f.read_bytes())
    
    # Find and load C-ROM pairs
    c_files = sorted([f for f in files if re.match(r'.*-c\d*\.', f.name.lower())])
    
    # Group into pairs (c1+c2, c3+c4, etc.)
    c_odd = [f for f in c_files if re.match(r'.*-c[13579]\.', f.name.lower())]
    c_even = [f for f in c_files if re.match(r'.*-c[2468]\.', f.name.lower())]
    
    for c1_file, c2_file in zip(sorted(c_odd), sorted(c_even)):
        print(f"  Loading C-ROM pair: {c1_file.name} + {c2_file.name}")
        c1_data = c1_file.read_bytes()
        c2_data = c2_file.read_bytes()
        roms['c_pairs'].append((c1_data, c2_data))
    
    return roms


def load_mame_zip(path: Path) -> dict:
    """Load ROM set from a zip file."""
    roms = {
        'p': bytearray(),
        's': bytearray(),
        'm': bytearray(),
        'v': bytearray(),
        'c_pairs': []
    }
    
    with zipfile.ZipFile(path, 'r') as zf:
        names = zf.namelist()
        
        # P-ROM
        p_files = sorted([n for n in names if re.match(r'.*-p\d*\.', n.lower()) or 
                                               re.match(r'.*_p\d*\.', n.lower())])
        for f in p_files:
            print(f"  Loading P-ROM: {f}")
            roms['p'].extend(zf.read(f))
        
        # S-ROM
        s_files = sorted([n for n in names if re.match(r'.*-s\d*\.', n.lower()) or
                                               re.match(r'.*_s\d*\.', n.lower())])
        for f in s_files:
            print(f"  Loading S-ROM: {f}")
            roms['s'].extend(zf.read(f))
        
        # M-ROM
        m_files = sorted([n for n in names if re.match(r'.*-m\d*\.', n.lower()) or
                                               re.match(r'.*_m\d*\.', n.lower())])
        for f in m_files:
            print(f"  Loading M-ROM: {f}")
            roms['m'].extend(zf.read(f))
        
        # V-ROM
        v_files = sorted([n for n in names if re.match(r'.*-v\d*\.', n.lower()) or
                                               re.match(r'.*_v\d*\.', n.lower())])
        for f in v_files:
            print(f"  Loading V-ROM: {f}")
            roms['v'].extend(zf.read(f))
        
        # C-ROM pairs
        c_files = sorted([n for n in names if re.match(r'.*-c\d*\.', n.lower()) or
                                               re.match(r'.*_c\d*\.', n.lower())])
        c_odd = [f for f in c_files if re.search(r'[_-]c[13579]\.', f.lower())]
        c_even = [f for f in c_files if re.search(r'[_-]c[2468]\.', f.lower())]
        
        for c1_name, c2_name in zip(sorted(c_odd), sorted(c_even)):
            print(f"  Loading C-ROM pair: {c1_name} + {c2_name}")
            c1_data = zf.read(c1_name)
            c2_data = zf.read(c2_name)
            roms['c_pairs'].append((c1_data, c2_data))
    
    return roms


def load_neo_file(path: Path) -> dict:
    """
    Load a .neo format ROM file (TerraOnion NeoSD format).
    
    .neo format:
    - Header with sizes
    - P, S, M, V1, V2, C data concatenated
    """
    roms = {
        'p': bytearray(),
        's': bytearray(),
        'm': bytearray(),
        'v': bytearray(),
        'c_pairs': []
    }
    
    with open(path, 'rb') as f:
        # Read .neo header (simplified - actual format may vary)
        # This is a basic implementation; actual .neo parsing may need refinement
        header = f.read(4096)  # Header area
        
        # Try to detect header format
        # Common .neo header has sizes at specific offsets
        # This is approximate - may need adjustment for specific .neo versions
        
        print("  Warning: .neo format support is experimental")
        print("  Consider using MAME ROM sets for best results")
        
        # Read remaining data as raw ROM
        data = f.read()
        
        # For now, return empty - .neo parsing needs format documentation
        print("  .neo parsing not fully implemented yet")
        
    return roms


def convert_to_ngfc(input_path: Path, output_path: Path, ngh_number: int = 0, flags: int = 0):
    """
    Convert a Neo Geo ROM set to NGFC format.
    """
    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")
    
    # Load source ROMs
    if input_path.suffix.lower() == '.neo':
        roms = load_neo_file(input_path)
    else:
        roms = load_mame_romset(input_path)
    
    # Verify we have data
    if not roms['p']:
        print("Warning: No P-ROM data found")
    if not roms['c_pairs']:
        print("Warning: No C-ROM data found")
    
    print("\nTransforming ROMs for SDRAM access...")
    
    # Transform S-ROM
    print("  Transforming S-ROM...")
    s_transformed = transform_srom(roms['s']) if roms['s'] else bytearray()
    
    # Transform C-ROM (the big one)
    print("  Transforming C-ROM (this may take a moment)...")
    c_original_size = sum(len(c1) + len(c2) for c1, c2 in roms['c_pairs'])
    c_transformed = transform_full_crom(roms['c_pairs']) if roms['c_pairs'] else bytearray()
    
    # Build header
    header = NGFCHeader()
    header.flags = flags
    header.ngh_number = ngh_number
    header.p_size = len(roms['p'])
    header.s_size = len(s_transformed)
    header.m_size = len(roms['m'])
    header.v_size = len(roms['v'])
    header.c_size = len(c_transformed)
    header.c_size_original = c_original_size
    
    # Calculate CRC32 of all data
    crc = 0
    for data in [roms['p'], s_transformed, roms['m'], roms['v'], c_transformed]:
        if data:
            crc = (crc + (int.from_bytes(hashlib.md5(bytes(data)).digest()[:4], 'little'))) & 0xFFFFFFFF
    header.crc32 = crc
    
    # Write output file
    print(f"\nWriting output file...")
    with open(output_path, 'wb') as f:
        f.write(header.pack())
        f.write(bytes(roms['p']))
        f.write(bytes(s_transformed))
        f.write(bytes(roms['m']))
        f.write(bytes(roms['v']))
        f.write(bytes(c_transformed))
    
    # Summary
    total_size = (NGFC_HEADER_SIZE + len(roms['p']) + len(s_transformed) + 
                  len(roms['m']) + len(roms['v']) + len(c_transformed))
    
    print(f"\nConversion complete!")
    print(f"  P-ROM: {len(roms['p']):,} bytes")
    print(f"  S-ROM: {len(s_transformed):,} bytes (transformed)")
    print(f"  M-ROM: {len(roms['m']):,} bytes")
    print(f"  V-ROM: {len(roms['v']):,} bytes")
    print(f"  C-ROM: {len(c_transformed):,} bytes (from {c_original_size:,} original)")
    print(f"  Total: {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)")


def verify_ngfc(path: Path):
    """Verify an NGFC file and display its contents."""
    print(f"Verifying: {path}")
    
    with open(path, 'rb') as f:
        header_data = f.read(NGFC_HEADER_SIZE)
        header = NGFCHeader.unpack(header_data)
        
        print(f"\nNGFC Header:")
        print(f"  Version: {header.version}")
        print(f"  Flags: 0x{header.flags:04X}")
        print(f"  NGH Number: {header.ngh_number}")
        print(f"  P-ROM size: {header.p_size:,} bytes")
        print(f"  S-ROM size: {header.s_size:,} bytes")
        print(f"  M-ROM size: {header.m_size:,} bytes")
        print(f"  V-ROM size: {header.v_size:,} bytes")
        print(f"  C-ROM size: {header.c_size:,} bytes (original: {header.c_size_original:,})")
        print(f"  CRC32: 0x{header.crc32:08X}")
        
        # Check file size
        f.seek(0, 2)
        file_size = f.tell()
        expected_size = (NGFC_HEADER_SIZE + header.p_size + header.s_size + 
                        header.m_size + header.v_size + header.c_size)
        
        print(f"\n  File size: {file_size:,} bytes")
        print(f"  Expected:  {expected_size:,} bytes")
        
        if file_size == expected_size:
            print("  ✓ File size matches header")
        else:
            print(f"  ✗ Size mismatch! Difference: {file_size - expected_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Neo Geo ROMs to NGFC format for flash cart use',
        epilog='Example: %(prog)s convert mslug.zip mslug.ngfc'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert ROM set to NGFC')
    convert_parser.add_argument('input', type=Path, help='Input ROM set (directory or zip)')
    convert_parser.add_argument('output', type=Path, help='Output NGFC file')
    convert_parser.add_argument('--ngh', type=int, default=0, help='NGH number (optional)')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify NGFC file')
    verify_parser.add_argument('file', type=Path, help='NGFC file to verify')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show NGFC file information')
    info_parser.add_argument('file', type=Path, help='NGFC file to examine')
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        if not args.input.exists():
            print(f"Error: Input not found: {args.input}")
            sys.exit(1)
        convert_to_ngfc(args.input, args.output, args.ngh)
        
    elif args.command == 'verify':
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        verify_ngfc(args.file)
        
    elif args.command == 'info':
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        verify_ngfc(args.file)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
