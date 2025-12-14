# neopico-cart

An open-source Neo Geo MVS/AES flash cartridge using SDRAM instead of expensive parallel SRAM, targeting ~$100 BOM vs ~$1500+ for existing solutions.

## Project Goals

- Support largest games (~96-128 MB total ROM)
- Acceptable load times (~12 seconds)
- Cost-effective design using SDRAM with prefetch (MiSTer-inspired approach)
- Open-source hardware and software

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flash Cart PCB                        │
│                                                          │
│  ┌──────────┐    ┌─────────────────┐    ┌───────────┐  │
│  │ SD Card  │───▶│   RP2350B MCU   │───▶│  128MB    │  │
│  │ (.ngfc   │    │   (Loader only) │    │  SDRAM    │  │
│  │  files)  │    └────────┬────────┘    └─────┬─────┘  │
│  └──────────┘             │                   │        │
│                           │ SPI              │ 16-bit  │
│                           ▼                   ▼        │
│              ┌─────────────────────────────────────┐   │
│              │         FPGA (ECP5 or Gowin)        │   │
│              │  • SDRAM controller (120MHz)        │   │
│              │  • Bank interleaving                │   │
│              │  • Neo Geo bus interface            │   │
│              │  • Level shifter control            │   │
│              └──────────────┬──────────────────────┘   │
│                             │                          │
└─────────────────────────────┼──────────────────────────┘
                              │ 5V Bus
                              ▼
                    ┌───────────────────┐
                    │   Neo Geo MVS/AES │
                    │   Cartridge Slot  │
                    └───────────────────┘
```

The key insight: microcontrollers cannot serve real-time bus data due to timing constraints (~40-60ns for C-ROM). Only FPGA + fast memory can meet these requirements. MiSTer proves SDRAM works with proper data reorganization and bank interleaving.

## Bill of Materials Estimate

| Component | Part | Est. Cost |
|-----------|------|-----------|
| FPGA | Gowin GW2A-18 or Lattice ECP5-25 | $20 |
| SDRAM | AS4C64M16D3 (128MB) | $10 |
| MCU | RP2350B | $2 |
| Flash | W25Q128 (16MB for menu/loader) | $2 |
| Level Shifters | TXB0108 or similar (×4) | $6 |
| SD Card Slot | micro-SD | $1 |
| Voltage Regulators | 3.3V, 1.2V | $2 |
| PCB | 4-layer, Neo Geo form factor | $15 |
| Passives & Connectors | | $10 |
| **Total** | | **~$70-80** |

With 30% margin for revisions: **~$100**

## Current Status

### Phase 1: Research & Tooling ✅ Complete

- [x] Analyze existing solutions (BackBit, MiSTer, NeoSD)
- [x] Document timing requirements
- [x] Extract MiSTer transformation algorithms
- [x] Create ROM converter tool
- [x] Define NGFC file format
- [x] Cost analysis

### Phase 2: FPGA Development (Next)

- [ ] Set up FPGA toolchain (Gowin or Lattice)
- [ ] Implement SDRAM controller with bank interleaving
- [ ] Benchmark SDRAM latency/bandwidth
- [ ] Implement Neo Geo bus sniffer (for timing analysis)

### Phase 3: Hardware Prototyping

- [ ] Design breakout board for FPGA dev kit → Neo Geo
- [ ] Measure real C-ROM timing on actual hardware
- [ ] Validate timing margins

### Phase 4+: Full Implementation, Testing, Release

## Tools

### NGFC Converter

The `ngfc/` directory contains a Python tool for converting standard Neo Geo ROM sets to the NGFC format, optimized for SDRAM burst access.

```bash
# Convert a MAME ROM set
./ngfc/ngfc_converter.py convert mslug.zip mslug.ngfc

# Verify an NGFC file
./ngfc/ngfc_converter.py verify mslug.ngfc
```

See [ngfc/README.md](ngfc/README.md) for full documentation.

## Documentation

- [Feasibility Study](docs/neogeo-flashcart-research.md) - Comprehensive technical analysis
- [NGFC Converter](ngfc/README.md) - ROM conversion tool documentation

## References

- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [MiSTer NeoGeo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [BackBit Platinum MVS](https://store.backbit.io/product/backbit-platinum-mvs/)

## License

See [LICENSE](LICENSE) for details.
