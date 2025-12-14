# neopico-cart

A Neo Geo MVS/AES flash cartridge using modern microcontrollers (RP2350) and FPGAs.

## Project Goals

- Support largest games (~96-128 MB total ROM)
- Acceptable load times (~12 seconds)
- Cost-effective design using SDRAM with prefetch (MiSTer-inspired approach)

## Architecture Overview

| Component | Role |
|-----------|------|
| **FPGA** | Real-time bus serving, SDRAM controller, sprite prefetch |
| **RP2350** | SD card interface, menu system, ROM loading |
| **SDRAM** | Main storage (~128 MB) with bank interleaving |

The key insight from existing solutions: microcontrollers cannot serve real-time bus data due to timing constraints (~40-60ns for C-ROM). Only FPGA + fast memory can meet these requirements.

## Technical Approach

Uses SDRAM with data reorganization (proven by MiSTer Neo Geo core):

1. Pre-transform ROM data at PC-side for SDRAM burst access
2. 4-bank interleaving at 120-144 MHz
3. Prefetch sprite tiles into FPGA BRAM cache
4. Serve from cache at full speed on PCK1B

## Documentation

- [Feasibility Study](docs/neogeo-flashcart-research.md) - Comprehensive technical analysis

## References

- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [MiSTer NeoGeo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [BackBit Platinum MVS](https://store.backbit.io/product/backbit-platinum-mvs/)

## Status

Research and feasibility study phase.

## License

See [LICENSE](LICENSE) for details.
