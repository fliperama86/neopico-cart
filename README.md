# neopico-cart

An open-source Neo Geo MVS/AES flash cartridge using SDRAM instead of expensive parallel SRAM, targeting ~$100 BOM vs ~$1500+ for existing solutions.

## Project Goals

- Support largest games (~96-128 MB total ROM)
- Fast load times (~4 seconds for largest games)
- Cost-effective design using SDRAM with bank interleaving (MiSTer-inspired)
- Open-source hardware and software

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                      Flash Cart PCB                       │
│                                                           │
│  ┌──────────┐      ┌─────────────┐      ┌─────────────┐  │
│  │ SD Card  │─SPI─▶│  RP2350B    │      │   128MB     │  │
│  │ (.ngfc)  │      │             │      │   SDRAM     │  │
│  └──────────┘      │ • SD/FAT32  │      └──────┬──────┘  │
│                    │ • Menu UI   │             │         │
│                    │ • Config    │         16-bit        │
│                    └──────┬──────┘             │         │
│                           │                    │         │
│                       PIO/QSPI                 │         │
│                      (20-30 MB/s)              │         │
│                           │                    │         │
│                           ▼                    ▼         │
│              ┌────────────────────────────────────────┐  │
│              │          FPGA (ECP5 or Gowin)          │  │
│              │  • SDRAM controller (120MHz)           │  │
│              │  • 4-bank interleaving                 │  │
│              │  • Neo Geo bus interface               │  │
│              │  • Menu video generation               │  │
│              └───────────────────┬────────────────────┘  │
│                                  │                       │
│                           Level Shifters                 │
│                                  │                       │
└──────────────────────────────────┼───────────────────────┘
                                   │ 5V Bus
                                   ▼
                         ┌───────────────────┐
                         │   Neo Geo MVS/AES │
                         │   Cartridge Slot  │
                         └───────────────────┘
```

### Why Two Chips?

**RP2350 (~$1.50)** handles "software" tasks that are easy in C but painful in HDL:
- SD card FAT32 filesystem parsing
- Menu system and user input
- Configuration and save management
- Uses PIO for high-speed FPGA data transfer (20-30 MB/s)

**FPGA** handles timing-critical tasks requiring nanosecond precision:
- SDRAM controller with 4-bank interleaving
- Neo Geo bus interface (~40-60ns response for C-ROM)
- Real-time data serving during gameplay

Microcontrollers cannot serve real-time bus data due to timing constraints. Only FPGA + fast memory can meet these requirements. MiSTer proves SDRAM works with proper data reorganization and bank interleaving.

### Boot Sequence

1. RP2350 boots, initializes FPGA (bitstream from flash)
2. RP2350 reads SD card, displays menu via FPGA video
3. User selects game
4. RP2350 streams .ngfc file to FPGA via PIO (~4 sec for largest games)
5. FPGA writes to SDRAM as data arrives
6. FPGA switches to "play" mode, serves all bus requests
7. RP2350 monitors for menu button combo

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
