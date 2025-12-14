# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a feasibility study and eventual implementation for a Neo Geo MVS/AES flash cartridge ("neopico-cart") using modern microcontrollers (RP2350) and/or FPGAs. The target is acceptable load times (~12 seconds) with no persistence requirement during gameplay.

## Key Technical Constraints

### Neo Geo Hardware Requirements

- **C-ROM timing is critical**: Data must be available within ~40-60ns of address latch
- **Total ROM for largest games**: ~96-128 MB (Garou: Mark of the Wolves is ~86 MB)
- Microcontrollers cannot serve real-time bus data; only FPGA/fast SRAM can meet timing

### Architecture Insights (from BackBit analysis)

- C-ROM requires 10ns parallel SRAM or SDRAM with bank interleaving + prefetch
- P/V/S/M-ROM buses have relaxed timing; PSRAM is acceptable
- RP2350 role: SD card, menu system, ROM loading (not real-time bus serving)

### MiSTer-Inspired SDRAM Approach

The most cost-effective approach uses SDRAM with data reorganization:
1. Pre-transform ROM data at PC-side for SDRAM burst access
2. Use 4-bank interleaving at 120-144 MHz
3. Prefetch sprite tiles into FPGA BRAM cache
4. Serve from cache at full speed on PCK1B

## ROM Data Transformations

### C-ROM Transformation (for SDRAM burst access)

Three-step process from MiSTer's `neogeo_loader.cpp`:
1. Interleave C1/C2 ROM pairs (bitplanes 0,1 + 2,3)
2. Byte swap for SDRAM word alignment: `[B3][B2][B1][B0]` → `[B3][B1][B2][B0]`
3. Reorder within 32-byte tiles for burst alignment using bit manipulation formula

### S-ROM Transformation

Convert column-major to line-major storage for burst reads.

## Reference Implementations

- **BackBit Platinum MVS**: Uses 10ns parallel SRAM for C-ROM (expensive)
- **MiSTer Neo Geo Core**: Uses SDRAM with prefetch (proven, well-documented)
- **TerraOnion NeoSD**: Uses .neo format (uncompressed, not reorganized)

## Key Resources

- `docs/neogeo-flashcart-research.md` - Comprehensive feasibility study and technical analysis
- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [MiSTer NeoGeo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- MiSTer's DEV_NOTES.md for SDRAM timing details
