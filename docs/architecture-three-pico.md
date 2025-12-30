# NeoPico-Cart Architecture: Triple RP2350 Design

## Overview

This document describes the "Triple Pico" architecture for the NeoPico-Cart — a Neo Geo MVS/AES flash cartridge using three RP2350 microcontrollers instead of FPGAs.

**Design Philosophy:**
- PSRAM data buses connect **directly** to Neo Geo (not through Picos)
- Picos handle **address translation only** (like BackBit's FPGA approach)
- Each Pico dedicated to specific timing domains
- Uses .ngfc pre-transformed ROM format

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PROG Board (Top)                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      PICO A (Master)                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│  │  │ SD Card      │  │ Menu/UI     │  │ Loading Coordinator  │  │   │
│  │  │ Interface    │  │ (Core 0)    │  │ (Core 1)             │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────────┐    │   │
│  │  │ P-ROM Address Control    │  │ V-ROM Address Control    │    │   │
│  │  │ (PIO 0)                  │  │ (PIO 1)                  │    │   │
│  │  └────────────┬─────────────┘  └────────────┬─────────────┘    │   │
│  └───────────────┼─────────────────────────────┼──────────────────┘   │
│                  │                             │                       │
│         ┌────────▼────────┐           ┌───────▼────────┐              │
│         │ P-ROM PSRAM     │           │ V-ROM PSRAM    │              │
│         │ (16MB)          │           │ (32MB)         │              │
│         └────────┬────────┘           └───────┬────────┘              │
│                  │ D0-D15                     │ SDRAD/SDPAD           │
│                  │ (direct)                   │ (direct)              │
├──────────────────┼─────────────────────────────┼──────────────────────┤
│                  │         FFC Link            │                      │
│                  │      (directly to PSRAM connections)               │
├──────────────────┼────────────────────────────┼───────────────────────┤
│                           CHA Board (Bottom)                          │
│                                                                        │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐   │
│  │      PICO B (C-ROM)         │    │    PICO C (S/M-ROM)         │   │
│  │  ┌───────────────────────┐  │    │  ┌───────────────────────┐  │   │
│  │  │ C-ROM Address Control │  │    │  │ S-ROM Address Control │  │   │
│  │  │ (PIO 0 + PIO 1)       │  │    │  │ (PIO 0)               │  │   │
│  │  │ PCK1B Handler         │  │    │  │ PCK2B Handler         │  │   │
│  │  └───────────┬───────────┘  │    │  └───────────┬───────────┘  │   │
│  │  ┌───────────┴───────────┐  │    │  ┌───────────────────────┐  │   │
│  │  │ P-Bus Address Capture │  │    │  │ M-ROM Address Control │  │   │
│  │  │ (74HC573 Latches)     │  │    │  │ (PIO 1)               │  │   │
│  │  └───────────────────────┘  │    │  └───────────┬───────────┘  │   │
│  └──────────────┬──────────────┘    └──────────────┼──────────────┘   │
│                 │                                   │                  │
│    ┌────────────▼────────────┐        ┌────────────▼────────────┐     │
│    │ C-ROM PSRAM Array       │        │ S-ROM      │ M-ROM      │     │
│    │ (8× 8MB = 64MB)         │        │ PSRAM      │ PSRAM      │     │
│    └────────────┬────────────┘        │ (1MB)      │ (1MB)      │     │
│                 │ CR0-CR31            └─────┬──────┴─────┬──────┘     │
│                 │ (direct)                  │ FIXD0-7    │ SDD0-7     │
│                 │                           │ (direct)   │ (direct)   │
├─────────────────┼───────────────────────────┼────────────┼────────────┤
│                 │                           │            │            │
│                 ▼                           ▼            ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      NEO GEO MAIN BOARD                         │ │
│  │   68000 CPU    LSPC    NEO-B1    NEO-ZMC2    YM2610    Z80     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Pico Assignments

### Pico A: Master Controller (PROG Board)

**Primary Responsibilities:**
- SD card interface and file system
- Menu system and user interface
- Game loading coordination
- P-ROM bus address control
- V-ROM bus address control

**Secondary Responsibilities:**
- Stream .ngfc data to Pico B/C during loading
- System coordination and status

| Resource | Allocation |
|----------|------------|
| Core 0 | Menu system, SD card, UI |
| Core 1 | Loading coordinator, P-ROM PIO management |
| PIO 0 | P-ROM address generation |
| PIO 1 | V-ROM address generation |
| PIO 2 | Inter-Pico communication |

### Pico B: C-ROM Controller (CHA Board)

**Primary Responsibilities:**
- C-ROM bus address control (most complex timing path)
- PCK1B signal handling
- P-bus address capture
- 8× PSRAM chip select management

**Timing Requirements:**
- <250ns from PCK1B edge to data valid
- Target: PSRAM address valid within ~20ns of PCK1B edge for fast access
- At 300MHz overclock: ~6 PIO cycles for address translation

| Resource | Allocation |
|----------|------------|
| Core 0 | Address translation, bank management |
| Core 1 | Cache/prefetch management (if needed) |
| PIO 0 | P-bus address capture |
| PIO 1 | PSRAM address output |
| PIO 2 | PCK1B edge detection, timing control |

### Pico C: S/M-ROM Controller (CHA Board)

**Primary Responsibilities:**
- S-ROM bus address control (fix layer)
- M-ROM bus address control (Z80 program)
- PCK2B signal handling

**Timing Requirements:**
- S-ROM: <200ns (relaxed compared to C-ROM)
- M-ROM: Relaxed (Z80 @ 4MHz)

| Resource | Allocation |
|----------|------------|
| Core 0 | S-ROM address management |
| Core 1 | M-ROM address management |
| PIO 0 | S-ROM address generation, PCK2B handling |
| PIO 1 | M-ROM address generation |
| PIO 2 | Inter-Pico communication |

---

## Pin Allocations

### Pico A: Master (PROG Board)

| Function | Signal | Pins | Direction |
|----------|--------|------|-----------|
| **P-ROM PSRAM Address** | PA0-PA19 | 20 | Output |
| **P-ROM PSRAM CS** | /PCS | 1 | Output |
| **P-ROM Control** | /ROMOE, R/W, AS | 3 | Input |
| **P-ROM Banking** | SLOTCS, SYSTEMB | 2 | Input |
| **V-ROM PSRAM Address** | VA0-VA19 | (shared with PA) | Output |
| **V-ROM PSRAM CS** | /VCS0, /VCS1 | 2 | Output |
| **V-ROM Control** | /SDRD0, /SDRD1 | 2 | Input |
| **V-ROM Mux** | /SDPOE, SDRMPX | 2 | Input |
| **SD Card SPI** | CS, CLK, MOSI, MISO | 4 | Mixed |
| **FFC Link** | TX, RX, CLK, SYNC | 4 | Mixed |
| **Status LED** | LED | 1 | Output |
| **Reserved** | - | 5 | - |
| **Total** | | **~42** | |

### Pico B: C-ROM (CHA Board)

| Function | Signal | Pins | Direction |
|----------|--------|------|-----------|
| **P-Bus Low** | P0-P15 | 16 | Input |
| **P-Bus High** | P16-P23 | 8 | Input |
| **CA4** | CA4 | 1 | Input |
| **C-ROM PSRAM Address** | CA0-CA21 | 22 | Output |
| **C-ROM PSRAM CS** | /CCS0-/CCS7 | 8 | Output |
| **Control Signals** | PCK1B, EVEN, H, LOAD | 4 | Input |
| **Clock Reference** | 12M | 1 | Input |
| **FFC Link** | TX, RX, CLK, SYNC | 4 | Mixed |
| **Total** | | **~48** | |

**Note:** Pico B is at GPIO limit. May use 74HC573 latches to reduce P-bus input pins.

### Pico C: S/M-ROM (CHA Board)

| Function | Signal | Pins | Direction |
|----------|--------|------|-----------|
| **S-ROM Address In** | (from P-bus via latch) | 12 | Input |
| **S-ROM PSRAM Address** | SA0-SA16 | 17 | Output |
| **S-ROM PSRAM CS** | /SCS | 1 | Output |
| **S-ROM Control** | PCK2B, 2H1 | 2 | Input |
| **M-ROM Address In** | SDA0-SDA15 | 16 | Input |
| **M-ROM PSRAM Address** | MA0-MA16 | (shared with SA) | Output |
| **M-ROM PSRAM CS** | /MCS | 1 | Output |
| **M-ROM Control** | /SDMRD, /SDROM | 2 | Input |
| **FFC Link** | TX, RX, CLK, SYNC | 4 | Mixed |
| **Reserved** | - | 6 | - |
| **Total** | | **~41** | |

---

## Memory Configuration

### PSRAM Allocation

| ROM Type | PSRAM Chips | Capacity | Controller |
|----------|-------------|----------|------------|
| C-ROM | 8× APS6404L-3SQR | 64 MB | Pico B |
| P-ROM | 2× APS6404L-3SQR | 16 MB | Pico A |
| V-ROM | 4× APS6404L-3SQR | 32 MB | Pico A |
| S-ROM | 1× APS6404L-3SQR | 128 KB used | Pico C |
| M-ROM | (shared with S) | 128 KB used | Pico C |
| **Total** | **15 chips** | **~120 MB** | |

### PSRAM Interface

Using QSPI PSRAM (e.g., APS6404L):
- 4-bit data width per chip
- 133 MHz max clock
- ~55ns random access latency

**Alternative:** Parallel PSRAM for lower latency but more pins.

For C-ROM (needs 32-bit output):
- Option 1: 8× QSPI PSRAM, parallel chip selects
- Option 2: 4× Octal PSRAM (8-bit each)
- Option 3: Parallel PSRAM with direct Neo Geo connection

**Recommended:** Parallel PSRAM for C-ROM (timing critical), QSPI for others.

---

## Data Flow

### Game Loading Sequence

```
1. User selects game from menu (Pico A)
2. Pico A reads .ngfc header from SD card
3. Pico A allocates PSRAM regions

4. P-ROM loading:
   └── Pico A streams P-ROM section → local PSRAM

5. V-ROM loading:
   └── Pico A streams V-ROM section → local PSRAM

6. C-ROM loading:
   ├── Pico A reads C-ROM section from SD
   ├── Pico A sends over FFC link to Pico B
   └── Pico B writes to C-ROM PSRAM array

7. S-ROM loading:
   ├── Pico A sends S-ROM section to Pico C
   └── Pico C writes to S-ROM PSRAM

8. M-ROM loading:
   ├── Pico A sends M-ROM section to Pico C
   └── Pico C writes to M-ROM PSRAM

9. All Picos switch to "serve" mode
10. Pico A releases Neo Geo reset (game starts)
```

**Expected load time:** ~10-15 seconds for largest games (comparable to BackBit).

### Runtime Data Flow

```
C-ROM Access (per tile):
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ LSPC puts   │───►│ Pico B      │───►│ PSRAM       │───►│ NEO-ZMC2    │
│ addr on     │    │ translates  │    │ outputs     │    │ serializes  │
│ P-bus       │    │ to PSRAM    │    │ CR0-31      │    │ to pixels   │
│             │    │ address     │    │ (direct)    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     PCK1B ────────────►│
                   ~20ns            ~55ns              ~10ns
                   └────────────── Total: <100ns ──────────────┘
```

---

## Timing Analysis

### C-ROM Critical Path

| Stage | Time | Notes |
|-------|------|-------|
| PCK1B edge detection | ~3ns | PIO input sync |
| Address capture | ~10ns | From latches or direct |
| Address translation | ~20ns | PIO + bank lookup |
| PSRAM chip select | ~5ns | GPIO output |
| PSRAM access | ~55ns | PSRAM datasheet |
| Data valid on bus | - | Direct connection |
| **Total** | **~93ns** | |

**Available time:** PCK1B period = 666ns, but data needed within <250ns (8 mclk window = ~333ns).

**Margin:** ~157ns — comfortable.

### P-ROM Path

| Stage | Time | Notes |
|-------|------|-------|
| Address valid | - | From 68000 |
| Address decode | ~30ns | PIO |
| PSRAM access | ~55ns | |
| Data valid | - | Direct |
| **Total** | **~85ns** | |

**Available time:** 150ns minimum (P-ROM spec).

**Margin:** ~65ns — acceptable.

---

## Bill of Materials (Estimated)

| Component | Quantity | Unit Cost | Total |
|-----------|----------|-----------|-------|
| RP2350B (QFN-60) | 3 | $1.50 | $4.50 |
| PSRAM APS6404L-3SQR | 15 | $3.00 | $45.00 |
| Level shifter TXB0108 | 12 | $1.50 | $18.00 |
| 74HC573 Latch | 4 | $0.50 | $2.00 |
| FFC connector (60-pin) | 2 | $1.00 | $2.00 |
| SD card slot | 1 | $1.00 | $1.00 |
| Crystal 12MHz | 3 | $0.30 | $0.90 |
| Voltage regulator 3.3V | 2 | $0.50 | $1.00 |
| Capacitors, resistors | ~50 | $0.02 | $1.00 |
| PCB (2-layer, 2 boards) | 1 set | $15.00 | $15.00 |
| Cartridge shell | 1 | $10.00 | $10.00 |
| **Total BOM** | | | **~$100** |

---

## Advantages

1. **No FPGA required** — All RP2350, single toolchain (C/PIO ASM)
2. **Proven architecture** — Based on BackBit's PSRAM-direct approach
3. **Cost effective** — ~$100 BOM vs $100-200 for BackBit
4. **Flexible** — Easy firmware updates via SD card
5. **Hackable** — Open source, well-documented
6. **.ngfc format** — No runtime data transformation

## Challenges

1. **Pin count tight on Pico B** — May need external latches
2. **PIO timing critical** — C-ROM path needs careful optimization
3. **Inter-Pico bandwidth** — Loading speed limited by FFC link
4. **PSRAM sourcing** — Need reliable supplier for 15 chips
5. **PCB complexity** — Two boards, many traces

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| PIO too slow for C-ROM | Add 74HC573 latches for address capture |
| PSRAM latency too high | Use parallel PSRAM instead of QSPI |
| Six-slot MVS timing | Optimize PIO, add pipelining |
| Inter-Pico bottleneck | Use parallel FFC, increase clock |

---

## Development Phases

### Phase 1: Bus Sniffer
- Build logic analyzer to capture real Neo Geo timing
- Verify assumptions about PCK1B, address setup times
- Test on various MVS boards (1-slot, 4-slot, 6-slot)

### Phase 2: Single Bus Prototype
- Implement P-ROM only on single Pico
- Validate PSRAM timing
- Test with simple homebrew ROM

### Phase 3: C-ROM Prototype
- Add Pico B for C-ROM
- Most timing-critical validation
- Test sprite rendering

### Phase 4: Full Integration
- Add Pico C for S/M-ROM
- Complete game loading
- Full compatibility testing

### Phase 5: PCB Design
- Design PROG and CHA boards
- Manufacture prototypes
- Case design

---

## References

- `docs/neogeo-mvs-cartridge-reference.md` — Hardware pinout and timing
- `docs/neopico-cart-rp2350-feasibility.md` — RP2350 feasibility analysis
- `docs/neogeo-flashcart-research.md` — BackBit/MiSTer research
- `docs/transcript.txt` — Evie's BackBit presentation
- `ngfc/README.md` — .ngfc format specification

---

*Document version: 1.0*
*Created: December 2024*
*Architecture: Triple RP2350 ("Three Pico")*
