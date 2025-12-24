# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a feasibility study and eventual implementation for a Neo Geo MVS/AES flash cartridge ("neopico-cart") using RP2350 microcontrollers. The target is acceptable load times (~12 seconds) with no persistence requirement during gameplay.

**Primary goal:** Build a Pico-only (no FPGA) Neo Geo flash cart using a cache-based architecture.

## Key Technical Constraints

### Neo Geo Hardware Requirements

- **C-ROM timing is critical**: Data must be available within ~40-60ns of address latch
- **Total ROM for largest games**: ~96-128 MB (Garou: Mark of the Wolves is ~86 MB)
- **80 bits of data buses**: P (16-bit), C (32-bit), S (8-bit), M (8-bit), V (16-bit)

### Architecture Insights (from BackBit - CORRECTED Dec 2024)

From Evie Salomon's VCF SoCal 2025 presentation (`docs/transcript.txt`):

- **BackBit uses PSRAM for ALL ROMs including C-ROM** (not 10ns SRAM as previously thought)
- PSRAM connects **directly** to Neo Geo data bus — no FPGA caching
- FPGA handles **addressing only** (banking, decoding)
- This validates PSRAM as viable for C-ROM timing

### RP2350 Cache-Based Approach

Since RP2350 PIO is sequential (unlike FPGA combinatorial logic), we use caching:

1. **Backing store**: PSRAM (simpler) or SDRAM (cheaper)
2. **Prefetch during H-blank**: ~15μs window to load next scanline's tiles
3. **Cache in RP2350 internal SRAM**: 520KB available (500× more than MiSTer's BRAM)
4. **Serve from cache via PIO**: Fast enough at 300MHz (~3.3ns/cycle)

The `.ngfc` format pre-transforms ROM data, eliminating real-time processing.

## ROM Data Transformations

### C-ROM Transformation (implemented in ngfc/)

Three-step process from MiSTer's `neogeo_loader.cpp`:

1. Interleave C1/C2 ROM pairs (bitplanes 0,1 + 2,3)
2. Byte swap for word alignment: `[B3][B2][B1][B0]` → `[B3][B1][B2][B0]`
3. Reorder within 32-byte tiles for burst alignment

### S-ROM Transformation

Convert column-major to line-major storage for sequential reads.

**Result:** One sequential read = complete tile line, no runtime transformation.

## Reference Implementations

- **BackBit Platinum MVS**: PSRAM + iCE40 FPGA (addressing only) — proven, simple
- **MiSTer Neo Geo Core**: SDRAM with prefetch + BRAM cache — well-documented
- **PicoGUS**: RP2040 + PSRAM for ISA bus — proves Pico can do real-time bus interfacing

## Project Structure

```
neopico-cart/
├── ngfc/                    # NGFC ROM converter tool (Python)
│   ├── ngfc_converter.py    # Converts MAME ROMs to .ngfc format
│   ├── test_ngfc_converter.py
│   └── README.md            # Format specification
├── docs/
│   ├── architecture-three-pico.md         # PRIMARY: 3× RP2350 architecture design
│   ├── neogeo-mvs-cartridge-reference.md  # Hardware reference (pinout, timing, buses)
│   ├── neogeo-flashcart-research.md       # Flash cart analysis, BackBit/MiSTer
│   ├── neopico-cart-rp2350-feasibility.md # RP2350 feasibility study
│   └── transcript.txt                     # Evie's VCF SoCal 2025 talk transcript
└── CLAUDE.md               # This file
```

## Key Resources

### Project Docs (READ THESE FIRST)
- `docs/architecture-three-pico.md` - **PRIMARY: 3× RP2350 architecture** (pin allocation, BOM, data flow)
- `docs/neogeo-mvs-cartridge-reference.md` - MVS hardware reference (pinout, timing, buses)
- `docs/neopico-cart-rp2350-feasibility.md` - RP2350 feasibility analysis
- `docs/neogeo-flashcart-research.md` - Flash cart analysis, BackBit/MiSTer details
- `docs/transcript.txt` - BackBit architecture source (Evie's VCF talk)
- `ngfc/README.md` - NGFC format specification

### External Resources
- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [MiSTer NeoGeo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [PicoGUS Project](https://github.com/polpo/picogus) - RP2040 real-time bus example
- [rp2040-psram Library](https://github.com/polpo/rp2040-psram)

## Important Notes for Claude

1. **READ ALL docs/*.md files** at the start of each session
2. BackBit uses **PSRAM, not 10ns SRAM** — this was corrected Dec 2024
3. The `.ngfc` format is critical — it eliminates runtime transformation
4. Focus on **RP2350-only** solutions unless user asks otherwise
