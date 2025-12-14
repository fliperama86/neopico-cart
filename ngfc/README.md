# NGFC Converter - Neo Geo Flash Cart ROM Converter

A Python tool for converting standard Neo Geo ROM sets to the NGFC format, optimized for SDRAM-based flash cartridges.

## Overview

This tool implements the data transformation algorithms used by the MiSTer FPGA Neo Geo core to reorganize ROM data for efficient SDRAM burst access. By pre-transforming ROMs on a PC, flash cart hardware can serve sprite data directly from SDRAM without real-time processing.

## Background

Neo Geo hardware expects sprite (C-ROM) data on a tight timing budget (~40-60ns). Standard SDRAM has ~60-90ns random access latency, making it seemingly unsuitable. However, SDRAM excels at **burst reads** where multiple sequential words are read efficiently.

The MiSTer Neo Geo core solved this by:
1. **Reorganizing ROM data** during loading so that SDRAM bursts return data in the exact order hardware expects
2. **Interleaving C-ROM pairs** (C1+C2, C3+C4) so all 4 bitplanes are sequential
3. **Byte-swapping** for proper SDRAM word alignment

This tool performs the same transformations offline, producing pre-optimized ROM files.

## Installation

```bash
# No dependencies beyond Python 3.6+ standard library
chmod +x ngfc_converter.py
```

## Usage

### Convert a ROM Set

```bash
# From MAME-format directory
./ngfc_converter.py convert /path/to/mslug/ mslug.ngfc

# From MAME-format zip file
./ngfc_converter.py convert mslug.zip mslug.ngfc

# With NGH number (optional)
./ngfc_converter.py convert mslug.zip mslug.ngfc --ngh 201
```

### Verify an NGFC File

```bash
./ngfc_converter.py verify mslug.ngfc
```

### Show File Information

```bash
./ngfc_converter.py info mslug.ngfc
```

## NGFC File Format

```
Header (64 bytes):
  Offset 0x00: Magic "NGFC" (4 bytes)
  Offset 0x04: Version (2 bytes)
  Offset 0x06: Flags (2 bytes)
  Offset 0x08: NGH number (4 bytes)
  Offset 0x0C: P-ROM size (4 bytes)
  Offset 0x10: S-ROM size (4 bytes)
  Offset 0x14: M-ROM size (4 bytes)
  Offset 0x18: V-ROM size (4 bytes)
  Offset 0x1C: C-ROM size (4 bytes) - after transformation
  Offset 0x20: Original C-ROM size (4 bytes)
  Offset 0x24: CRC32 (4 bytes)
  Offset 0x28: Reserved (24 bytes)

Data sections (in order):
  P-ROM: Program code (original format)
  S-ROM: Fix layer graphics (transformed for burst access)
  M-ROM: Z80 sound program (original format)
  V-ROM: ADPCM audio samples (original format)
  C-ROM: Sprite graphics (transformed for SDRAM burst access)
```

## Transformation Algorithms

### C-ROM Transformation

Three-step process based on MiSTer's `neogeo_loader.cpp`:

1. **Interleave C1/C2 pairs**: Merge separate bitplane files
   ```
   Output pattern: C2 C2 C1 C1 C2 C2 C1 C1...
   ```

2. **Byte swap**: Reorder bytes within 32-bit words
   ```
   [B3][B2][B1][B0] → [B3][B1][B2][B0]
   ```

3. **Burst reorder**: Permute bytes within 32-byte blocks
   ```c
   j = (i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)
   ```

### S-ROM Transformation

Convert from column-major to line-major storage:
```
Original: column 2, column 3, column 0, column 1 (each 8 lines)
Output:   line 0 cols 0-3, line 1 cols 0-3, etc.
```

## Supported Input Formats

- **MAME ROM sets** (directory or zip)
  - Files named: `*-p1.bin`, `*-c1.bin`, `*-c2.bin`, etc.
  - Standard MAME naming conventions

- **TerraOnion .neo format** (experimental)
  - Basic support, may need refinement

## Output Characteristics

- **Single file**: All ROMs combined into one `.ngfc` file
- **Pre-transformed**: Ready for direct SDRAM loading
- **Larger than original**: C-ROM doubles due to interleaving (C1+C2 merged)
- **Typical sizes**: 20-100 MB depending on game

## Testing

```bash
python3 test_ngfc_converter.py
```

All transformation algorithms are tested against expected MiSTer behavior.

## Technical References

- [MiSTer Neo Geo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [MiSTer neogeo_loader.cpp](https://github.com/MiSTer-devel/Main_MiSTer/blob/master/support/neogeo/neogeo_loader.cpp)
- [Furrtek's DEV_NOTES.md](https://github.com/MiSTer-devel/NeoGeo_MiSTer/blob/master/DEV_NOTES.md)
- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)

## License

GPL v3 (same as MiSTer project, as algorithms are derived from MiSTer source code)

## Disclaimer

This tool is for personal backup and development purposes. Please respect game copyrights and only use with legally obtained ROM files.
