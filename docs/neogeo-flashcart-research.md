# Neo Geo Flash Cart Feasibility Study

## Project Goal

Evaluate the feasibility of building a Neo Geo MVS/AES flash cartridge using modern microcontrollers (RP2350) and/or FPGAs, with acceptable load times (~12 seconds) and no persistence requirement during gameplay.

---

## Neo Geo Hardware Overview

### System Architecture

The Neo Geo uses a multi-bus architecture with separate ROM buses for different subsystems:

| Bus | Purpose | Size (Largest Games) | Timing Criticality |
|-----|---------|---------------------|-------------------|
| **C-ROM** | Sprite graphics | ~64 MB (Garou/KOF) | **Critical** (real-time rendering) |
| **S-ROM** | Fix layer graphics | ~512 KB | Medium |
| **M-ROM** | Z80 sound program | ~128 KB | Low |
| **V-ROM** | ADPCM audio samples | ~48 MB (KOF 2003) | Medium (buffered) |
| **P-ROM** | 68000 program code | ~8 MB (KOF 2003) | High (CPU wait states) |
| **Total** | **All ROMs** | **~128 MB (Max Official)** | **Target Capacity** |
new_string_2:
**Total ROM for largest games**: ~128 MB (Garou: Mark of the Wolves is ~86 MB total)

### Critical Timing Constraints

From the [NeoGeo Development Wiki](https://wiki.neogeodev.org/):

- **Master clock**: 24 MHz (1 mclk = 41.67 ns)
- **C-ROM rendering**: 16 mclk per sprite tile line = 666.7 ns total
- **C-ROM reads per tile**: 2 reads per 16-pixel line = 333.3 ns per access
- **PCK1B latch frequency**: 1.5 MHz (55 ns low, 610 ns high)
- **C-ROM access requirement**: <250 ns (~8 mclk window, per NeoGeo Dev Wiki)
- **NEO-ZMC2 serializer**: 12 MHz clock (internal timing, not the C-ROM requirement)
- **Minimum VRAM access**: ~45 ns (1.5 mclk = 62.5 ns slots)

**Key insight**: The C-ROM bus requires data within **<250ns** of address latch. This is comfortable for PSRAM (55ns access) as BackBit demonstrates.

---

## Existing Solutions Analysis

### BackBit Platinum MVS

**Source**: Evie Salomon's VCF SoCal 2025 presentation

The BackBit Platinum is a commercial Neo Geo flash cart that provides key architectural insights.

#### Hardware Architecture

**Two-board design**:
1. **PROG Board**: Handles P-ROM (68000) and memory card buses
2. **CHA Board**: Handles Z80, C-ROM, S-ROM buses

**Memory Configuration**:

| ROM Type | Memory Technology | Details |
|----------|------------------|---------|
| All ROMs | **PSRAM** | Pseudo-Static RAM stores entire loaded game |

From Evie's VCF SoCal 2025 presentation:
> - *"PSRAM (Pseudo-Static Random Access Memory) stores loaded game"*
> - *"The FPGA plays traffic cop to serve PSRAM to the NEO GEO, support banking and emulating the link"*
> - *"The data lines of the RAM chips are connected to the CPU, but not to the FPGA"*

**Key insight**: PSRAM serves data **directly** to Neo Geo buses — the FPGA only handles address translation and banking, NOT data. No FPGA BRAM caching required!

**Why PSRAM works** (from Evie):
> *"The nice thing about the PS RAM is that on the outside, it operates just like a traditional static RAM chip from way back when. So, it can serve data pretty quick without having to send it a lot of series of commands."*

This avoids high-speed PCB design (>25-50 MHz) required for SDRAM.

**FPGA Configuration**:
- 2× Lattice iCE40 FPGAs (largest flat-pack version to avoid BGA assembly costs)
- Functions: Address decode, bank switching, link emulation
- **FPGA is NOT in the data path** — saves pins and latency
- FPGA controls PSRAM address lines; PSRAM data lines connect directly to Neo Geo

**Memory Configuration**:
- 8× PSRAM chips for C-ROM (64 MB total, ~8 MB each)
- Additional PSRAM for P/V/S/M-ROM

**Microcontroller (STM32)**:
- Role: SD card access, menu system, loading ROM data into PSRAM
- **NOT involved in real-time bus serving**
- Pipelines data over 80-bit bus to FPGAs during loading
- Total load time: ~12 seconds for largest games

**Key challenges mentioned**:
- **Metastability**: Unsettled FPGA inputs can cascade unknown states through gate chains
- **Six-slot MVS machines**: Bus multiplexing across 6 slots adds significant latency
- **Bidirectional address bus**: Input from Neo Geo, output to PSRAM requires careful timing
- **Level shifter latency**: Must use direction-specified shifters (not auto-sensing) to minimize delay

#### Key Insights from BackBit

1. **PSRAM is fast enough for ALL ROMs including C-ROM** — no caching needed, direct bus connection
2. **FPGA handles addressing only** — data path is PSRAM → Neo Geo directly (saves FPGA pins)
3. **Microcontrollers cannot serve real-time bus data** — only for loading/menu
4. **PSRAM behaves like classic SRAM** — simple interface, no command sequences like SDRAM
5. **Avoids high-speed PCB design** — staying under 25-50 MHz simplifies layout
6. **12-second load time is acceptable** — users tolerate this for the capability
7. **Latency optimization is critical** — metastability, level shifters, bus direction all add up

#### BackBit Cost Implications

Estimated BOM for the PSRAM + FPGA approach:
- ~10× PSRAM chips (8 for C-ROM + others): ~$40-80
- 2× iCE40 FPGAs (flat-pack, not BGA): ~$10-20
- Level shifters (TI, direction-specified): ~$20-40
- STM32 MCU: ~$5-10
- Passives, connectors, PCBs: ~$30-50
- **Total estimated BOM: ~$105-200**

This is significantly cheaper than fast parallel SRAM would be, making the $400 pre-order / $500 retail pricing profitable.

---

### MiSTer FPGA Neo Geo Core

**Source**: Furrtek's NeoGeo_MiSTer repository, DEV_NOTES.md, community discussions

The MiSTer Neo Geo core solves the same fundamental problem (feeding C-ROM data fast enough) but with a completely different approach.

#### Architecture Differences

| Aspect | BackBit (Real Hardware) | MiSTer (FPGA Emulation) |
|--------|------------------------|------------------------|
| Memory Type | 10ns Parallel SRAM | **SDR SDRAM @ 120-144 MHz** |
| Memory Cost (128MB) | ~$1500+ | **~$30-50 (single chip!)** |
| How it works | Direct bus connection | Pre-arranged data, burst reads |
| Timing constraint | Must respond to real Neo Geo | **Is** the Neo Geo, can adjust timing |

#### How MiSTer Makes SDRAM Work

From DEV_NOTES.md:

> *"The SDRAM extension board stores the 68k program, sprites and fix graphics. It currently runs at **120MHz** but may be pushed up to **144MHz** if needed."*

> *"The sprite data is **re-organized during loading** so that the bitplane data can be read in **4-word bursts** and used as-is."*

**Key techniques**:

1. **Data reorganization at load time**
   - ARM CPU shuffles ROM data into SDRAM-optimal layout
   - Sprite tiles arranged for sequential burst access
   - Fix graphics reordered to minimize random access

2. **Burst mode reads**
   - Read 4 words (64 bits) per burst instead of single words
   - First word: ~20 ns, subsequent words: ~8 ns each
   - 4-word burst = ~44 ns for 64 bits

3. **Bank interleaving**
   - SDRAM has 4 independent banks
   - While one bank completes access, start another
   - Achieves ~4× effective bandwidth

4. **Smart scheduling**
   - FPGA knows which subsystem needs data next
   - Schedules accesses to maximize parallelism
   - Uses auto-precharge to close rows automatically

#### SDRAM Bank Interleaving Explained

Standard SDRAM random access timing:
```
Single read cycle: ACT → wait(tRCD) → RD → wait(CL) → DATA
Total: ~60-90 ns per word at 100 MHz
```

With 4-bank interleaving:
```
Clock:  1    2    3    4    5    6    7    8    9    10
Bank 0: ACT  ---  RD   ---  ---  DATA ---  ---  ---  ACT...
Bank 1: ---  ACT  ---  RD   ---  ---  DATA ---  ---  ---
Bank 2: ---  ---  ACT  ---  RD   ---  ---  DATA ---  ---
Bank 3: ---  ---  ---  ACT  ---  RD   ---  ---  DATA ---
DQ Bus:                          D0   D1   D2   D3
```

**Result**: After pipeline fill, one word every ~2.5 cycles instead of ~9 cycles = **~4× throughput**

#### MiSTer Bandwidth Analysis

At 120 MHz with interleaving and 4-word bursts:
- ~50 ns per 64-bit tile line
- Theoretical max: ~160 MB/s
- Usable (after refresh, other accesses): ~80-100 MB/s

Neo Geo sprite requirements:
- Worst case: 96 tiles × 262 lines × 60 fps = ~1.5 million tile reads/sec
- Each tile = 64 bits = ~12 MB/s peak for sprites

**Conclusion**: SDRAM bandwidth is ~8× what's needed for sprites, with plenty left for CPU and audio.

#### Why MiSTer's Approach Works

The critical difference: **MiSTer IS the Neo Geo**.

- The FPGA implements the LSPC, NEO-ZMC2, and all other chips
- It can reorganize its internal pipeline to accommodate SDRAM latency
- It can prefetch data before it's needed
- It doesn't have to meet external timing constraints

A flash cart doesn't have this luxury — it must interface with **real** Neo Geo hardware that expects data on specific bus cycles.

---

## MiSTer Source Code Analysis

### Overview

The MiSTer Neo Geo core is the best-documented working example of SDRAM-based sprite delivery. By analyzing the actual source code, we can extract the exact algorithms needed for a potential flash cart design.

**Key files:**
- `neogeo_loader.cpp` — ROM loading and data transformation (Linux side)
- `sdram.sv` — SDRAM controller (FPGA side)  
- `sdram_mux.sv` — Memory access multiplexer
- `neogeo.sv` — Top-level core with memory addressing

### Sprite (C-ROM) Data Transformation

From `neogeo_loader.cpp`, the critical transformation function:

```cpp
// Fix layer (S-ROM) transformation for SDRAM burst access
// Comment from source: "To take advantage of the SDRAM burst read feature, 
// the data can be loaded so that all 8 pixels of a tile line can be read sequentially"

for (uint32_t i = 0; i < size; i++) 
    buf_out[i] = buf_in[(i & ~0x1F) | ((i >> 2) & 7) | ((i & 1) << 3) | (((i & 2) << 3) ^ 0x10)];
```

**Breaking down the bit manipulation:**
```
Input byte index:    i = AAAAA_BBBBB (where AAAAA is high bits, BBBBB is low 5 bits)
                         bits [31:5] | bits [4:0]

Output index formula:
  (i & ~0x1F)           → Keep high bits unchanged (tile boundary)
  | ((i >> 2) & 7)      → Bits 4:2 → position 2:0 (shift for burst alignment)
  | ((i & 1) << 3)      → Bit 0 → position 3 (odd/even byte swap)
  | (((i & 2) << 3) ^ 0x10) → Bit 1 → position 4, XOR with 0x10

Result: Data is reordered within each 32-byte tile so SDRAM bursts return 
        pixels in the order the video hardware needs them.
```

### C-ROM Byte Swapping

Also from `neogeo_loader.cpp`:

```cpp
// C-ROM loading includes byte swapping for SDRAM word alignment
for (uint32_t i = 0; i < size; i++) 
    buf[i] = (buf[i] & 0xFF0000FF) | ((buf[i] & 0xFF00) << 8) | ((buf[i] & 0xFF0000) >> 8);
```

This swaps the middle two bytes of each 32-bit word:
```
Input:  [B3][B2][B1][B0]
Output: [B3][B1][B2][B0]
```

Why? The original C-ROM pairs (C1+C2, C3+C4) store bitplanes split across chips. This swap interleaves them for sequential SDRAM access.

### SDRAM Address Mapping

From `DEV_NOTES.md` — how C-ROM addresses are mapped to SDRAM:

```
C-ROM index bits: x1BBBBBS
  B: 512KB bank number (5 bits = 32 banks)
  S: word shift (used to interleave odd/even ROMs)

SDRAM address = 0x0800000 + 0b1_BBBBB000_00000000_000000S0 + ioctl_addr
```

This places C-ROM data at offset 0x0800000 (8 MB) in SDRAM, with each 512KB bank aligned to SDRAM row boundaries for efficient burst access.

### Sprite Data Flow in Hardware

From `DEV_NOTES.md`:

```
1. PCK1B rises → triggers SDRAM read
2. SDRAM controller performs 4-word burst read
3. 64 bits (complete 16-pixel tile line) arrives
4. CA4 signal selects which 8-pixel group feeds NEO-ZMC2
5. CLK_12M latches data when LOAD is high
```

**Timing budget:**
- PCK1B period: ~666 ns
- SDRAM burst read (4 words): ~44 ns at 120 MHz
- Data muxing and output: ~10 ns
- **Margin: ~600 ns** — plenty of time!

### Fix Layer (S-ROM) Transformation

The fix layer uses a different transformation optimized for its access pattern:

```
Original storage (column-major, as in ROM):
  column 2 (lines 0~7), column 3 (lines 0~7), column 0 (lines 0~7), column 1 (lines 0~7)

SDRAM storage (line-major, for burst access):
  line 0 (columns 0~3), line 1 (columns 0~3), ...

Byte remapping:
  Original: 10 18 00 08 11 19 01 09 12 1A 02 0A 13 1B 03 0B ...
  SDRAM:    10-18 00-08 11-19 01-09 12-1A 02-0A 13-1B 03-0B ...
```

### SDRAM Controller Parameters

From the source code comments:

```
SDRAM clock: 120 MHz (may push to 144 MHz)
Configuration: SDR SDRAM, CL2 or CL3
Row activation (tRCD): 2-3 clocks
CAS latency: 2-3 clocks
Burst length: 4 words
Bank interleaving: Yes (4 banks)
Auto-precharge: Used for most reads
```

### Data Interleaving Pattern

The C-ROM data is interleaved as follows:

```
Original C-ROM pairs:
  C1: Bitplanes 0, 1 for tiles 0-N
  C2: Bitplanes 2, 3 for tiles 0-N

After transformation for SDRAM:
  Byte order: C2 C2 C1 C1 C2 C2 C1 C1 ...
  Bitplane order per line: 0 1 2 3 0 1 2 3 ...

Complete 16-pixel line = 4 bitplanes × 16 pixels = 64 bits = four 16-bit SDRAM words
```

This means ONE burst read returns an entire tile line ready for the NEO-ZMC2.

### Key Implementation Insights

1. **Pre-transformation is essential**: The ARM CPU on MiSTer spends significant time reorganizing ROM data during loading. This is a one-time cost that enables efficient runtime access.

2. **Burst alignment matters**: Data must be aligned so that a single SDRAM burst returns exactly what the hardware needs — no wasted bandwidth on unused bytes.

3. **Bank interleaving is the key**: Without interleaving, SDRAM would be far too slow. With it, effective latency drops from ~70 ns to ~20 ns.

4. **Prefetch window exists**: PCK1B gives ~666 ns to fetch 64 bits. Even with SDRAM latency, there's plenty of margin.

5. **Real-time transformation impossible**: The bit manipulation required cannot be done in real-time at 24 MHz. Must be pre-computed.

---

## Memory Technology Analysis

### Parallel SRAM

| Speed | Part Example | Density | Chips for 80MB | Cost/Chip | Total Cost |
|-------|-------------|---------|----------------|-----------|------------|
| 10 ns | AS6C4008 | 4 Mbit | 160 | ~$8-12 | ~$1280-1920 |
| 45 ns | AS6C8008 | 8 Mbit | 80 | ~$8.60 | ~$688 |
| 55 ns | AS6C8008 | 8 Mbit | 80 | ~$5.60 | ~$448 |

**Verdict**: Only 10 ns SRAM meets C-ROM timing directly. Slower SRAM might work with interleaving.

### PSRAM (Pseudo-Static RAM)

**Octal PSRAM** (APMemory APS12808L):
- Access time: 70-150 ns random access
- Cost: 128 Mbit (16 MB) ~$4.60 each
- 80 MB = ~$28 total (6 chips)
- **Verdict**: **Proven to work for ALL ROMs including C-ROM** (BackBit)

**QPI PSRAM**:
- Similar timing to Octal
- BackBit uses PSRAM for ALL ROM types including C-ROM

**Key insight from BackBit**: PSRAM works for C-ROM **without caching**. From Evie:
> *"The nice thing about the PS RAM is that on the outside, it operates just like a traditional static RAM chip from way back when. So, it can serve data pretty quick without having to send it a lot of series of commands."*

The architecture:
1. PSRAM data lines connect **directly** to Neo Geo buses
2. FPGA handles address translation/banking only (not in data path)
3. No high-speed PCB design needed (stays under 25-50 MHz)

This is simpler than SDRAM approaches and avoids FPGA BRAM caching complexity.

### HyperRAM

- Command/Address phase: 3 clock cycles (18 ns at 166 MHz)
- Initial access latency: 3-6 clock cycles
- **Total first-byte latency: ~54 ns minimum** at 166 MHz
- Burst throughput: 333-400 MB/s
- Cost: 64 Mbit (8 MB) ~$8 each, 80 MB = ~$80

**Verdict**: Latency too high for random C-ROM access, but excellent for sequential/burst workloads.

### SDR SDRAM

- Row activation (tRCD): ~15-20 ns
- CAS latency (CL2/CL3): 2-3 clocks = ~20-30 ns at 100 MHz
- Row precharge (tRP): ~15-20 ns
- **Single random access: ~60-90 ns**
- **With bank interleaving: ~15-20 ns effective**
- Cost: 512 Mbit (64 MB) ~$5-10 each

**Verdict**: Too slow for direct random access, but **viable with bank interleaving and prefetching** (as proven by MiSTer).

### RLDRAM3 (Reduced Latency DRAM)

- Designed for random access: 8-16 banks
- Access time: ~10 ns random access
- Cost: 576 Mbit-1 Gbit ~$30-50 each
- **Verdict**: Best DRAM for random access, but expensive and hard to source

---

## RP2350 Role Analysis

### What RP2350 Can Do

- SD card interface and file management
- Menu system and UI
- Loading ROM data into RAM (replacing STM32)
- Control signals to FPGA
- Dual QSPI support for faster loading
- PIO state machines for custom protocols

### What RP2350 Cannot Do

**Real-time bus serving** — confirmed impossible by Evie Salomon:

> *"The timing would be way too tight to do that with any microcontroller"*

The RP2350 runs at 150 MHz (6.67 ns/cycle). A C-ROM access requires:
- Detect address on bus
- Decode address
- Fetch data from memory
- Place data on bus

With the actual <250ns requirement (not the previously assumed ~40-60ns), PSRAM-based solutions become viable. The RP2350's PIO can handle address translation while PSRAM serves data directly to the Neo Geo bus, similar to BackBit's architecture.

### RP2350 Advantages Over STM32

- Lower cost
- More GPIO for control
- Dual-core for parallel tasks
- PIO for fast protocol handling
- Better availability

---

## Alternative Design Strategies

### Strategy 1: Interleaved Slower SRAM

Use 2+ banks of 55 ns SRAM with alternating access:
- While Bank A settling, Bank B delivers data
- Requires address prediction in FPGA
- Neo Geo sprite rendering is somewhat predictable (vertical strips)

**Cost**: ~$448 for 80 MB (vs $1500+ for 10ns)

**Risk**: Requires careful timing validation on real hardware

### Strategy 2: Hybrid Cache + Backing Store

- Small fast cache: 256 KB-1 MB of 10 ns SRAM
- Large backing store: 80 MB PSRAM/HyperRAM
- Cache sprite tiles as accessed

**Cost**: ~$100-150 total

**Risk**: Cache misses during rendering cause visible glitches

### Strategy 3: SDRAM with Prefetch (MiSTer-inspired)

This is the most promising cost-reduction approach:

```
┌─────────────────────────────────────────────────────────┐
│                    FPGA (ECP5/Gowin)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Sprite Prefetch Engine                  │  │
│  │  1. Monitor LSPC sprite evaluation signals        │  │
│  │  2. Predict next ~8 sprite tiles needed           │  │
│  │  3. Prefetch from SDRAM into tile cache           │  │
│  │  4. Serve data from cache on PCK1B                │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │       Tile Line Cache (FPGA BRAM)                 │  │
│  │       ~8-16 tile lines = 512-1024 bytes           │  │
│  │       Access time: 1 FPGA clock (~8 ns)           │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │    Bank-Interleaved SDRAM Controller              │  │
│  │    @ 120-144 MHz, 4-bank interleaving             │  │
│  │    4-word burst reads                             │  │
│  │    ~40-50 ns per tile line (64 bits)              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
             ┌─────────────────────────┐
             │    128 MB SDR SDRAM     │
             │    (AS4C32M16SB)        │
             │    ~$5-10 per chip      │
             └─────────────────────────┘
```

**How prefetch works**:
1. LSPC evaluates sprites during horizontal blanking (~15 μs before rendering)
2. FPGA snoops sprite evaluation to see which tiles are coming
3. Prefetches tile data from SDRAM into BRAM cache
4. When PCK1B fires, serves data from cache in ~10 ns

**Timing budget**:
- 15 μs (15,000 ns) to prefetch ~96 tiles
- 96 tiles × 50 ns = 4,800 ns
- **Plenty of margin!**

**Cost**: ~$45 total (SDRAM + FPGA)

**Risk**: Requires deep understanding of LSPC timing; cache misses cause glitches

### Strategy 4: "Lite" Cart for Smaller Games

Support only games up to 32 MB C-ROM (most pre-1996 titles):
- 32× 8 Mbit 55 ns SRAM = ~$180 for C-ROM
- Covers: Fatal Fury series, Art of Fighting, Samurai Shodown 1-2, Metal Slug 1, etc.

**Cost**: ~$250-300 total BOM

**Risk**: Limited game compatibility

---

## Cost Comparison Summary

| Approach | Memory Cost | FPGA/Logic | Total BOM |
|----------|-------------|------------|-----------|
| BackBit (PSRAM + FPGA cache) | ~$30-60 | ~$20-50 | ~$100-210 |
| 55ns SRAM Interleaved | ~$450 | ~$40 | ~$500 |
| Hybrid Cache | ~$100 | ~$40 | ~$200 |
| SDRAM + Prefetch | ~$10 | ~$50 | ~$100 |
| Lite Cart (32MB) | ~$180 | ~$40 | ~$250 |

**Note**: BackBit's PSRAM approach is comparable in cost to SDRAM + prefetch, validating that expensive fast SRAM is not required.

---

## Critical Unknowns (Updated)

1. ~~**Can slower memory work for C-ROM?**~~ — **ANSWERED: Yes!** BackBit proves PSRAM works with direct connection (no caching!)
2. ~~**Is FPGA caching required?**~~ — **ANSWERED: No!** PSRAM connects directly to Neo Geo data bus; FPGA handles addressing only
3. **Exact PSRAM part numbers used?** — Evie mentions 8 MB chips for C-ROM, but specific parts unknown
4. **Which iCE40 variant?** — "Largest flat-pack" suggests iCE40HX4K or HX8K in TQFP package
5. **Six-slot MVS compatibility** — Evie mentioned this required additional latency optimization
6. **Exact NEO-ZMC2 timing margins?** — No detailed timing diagrams found

---

## NeoPico-Cart Implementation

Based on this research, a concrete architecture has been designed for the NeoPico-Cart project:

**See: `docs/architecture-three-pico.md`**

The "Triple Pico" design uses 3× RP2350 microcontrollers instead of FPGAs:
- PSRAM connects directly to Neo Geo data buses (like BackBit)
- Picos handle address translation only (like BackBit's FPGAs)
- .ngfc format eliminates runtime data transformation
- Estimated BOM: ~$100

---

## Recommended Next Steps

### Phase 1: Research & Planning
1. Study MiSTer Neo Geo source code (SDRAM controller, sprite rendering)
2. Document LSPC sprite evaluation timing from NeoGeo Dev Wiki
3. Analyze feasibility of prefetch prediction

### Phase 2: Prototyping
1. Acquire dev board (Tang Nano 20K, ULX3S, or similar)
2. Implement basic SDRAM controller with bank interleaving
3. Test achievable bandwidth and latency

### Phase 3: Hardware Testing
1. Build simple logic analyzer to capture Neo Geo bus timing
2. Measure actual C-ROM access timing requirements
3. Test interleaved SRAM approach on real hardware

### Phase 4: Integration
1. Design PCB with chosen architecture
2. Implement full flash cart logic
3. Test with variety of games

---

---

## ROM Format Analysis

### TerraOnion NeoSD .neo Format

The NeoSD uses a proprietary `.neo` ROM format created by TerraOnion's NeoBuilder tool.

**Key characteristics:**
- Simple container format with header + concatenated ROM data
- Data is **uncompressed and decrypted**
- ROMs are stored in order: P, S, M, V1, V2, C

**Header structure** (from TerraOnion Wiki):
```
Header contains sizes for each ROM section:
- PSize: Program ROM size (max 1+8 MB)
- SSize: Fix tiles size (max 512 KB)  
- MSize: Z80 program size (max 256 KB)
- V1Size: ADPCM-A samples
- V2Size: ADPCM-B samples (0 if merged with V1)
- CSize: Sprite graphics (max 64 MB officially, larger for hacks)

Data follows header in P, S, M, V1, V2, C order
```

**Important insight**: The .neo format does **NOT** appear to reorganize sprite data for optimized access — it simply concatenates the decrypted ROMs. Any data reorganization for faster access must happen during loading into the flash cart's memory.

### NeoSD Hardware Architecture

From TerraOnion documentation:

- **Processor**: ARM Cortex M4 @ 168 MHz
- **FPGAs**: Two Lattice XP2 FPGAs
- **Memory**: 768 Mbit flash (enough for largest games)
- **NeoSD Pro**: 3840 Mbit total (4× flash slots + 1× SRAM slot)

The NeoSD Pro's RAM slot has "very fast loading times" compared to flash, suggesting they use SRAM for the volatile slot — similar to BackBit's approach.

### MiSTer ROM Data Reorganization

**This is critical**: MiSTer reorganizes ROM data during loading to optimize SDRAM access patterns.

From DEV_NOTES.md:

**Fix layer (S-ROM) reorganization:**
> *"The fix data is re-organized during loading so that pixel pairs are kept adjacent in the SDRAM. This allows to do only one read for 4 pixels."*

Original storage (column-major):
```
column 2 (lines 0~7), column 3 (lines 0~7), column 0 (lines 0~7), column 1 (lines 0~7)
```

Reorganized for SDRAM (line-major):
```
line 0 (columns 0~3), line 1 (columns 0~3)...
```

**Sprite graphics (C-ROM) reorganization:**
> *"The sprite data is re-organized during loading so that the bitplane data can be read in 4-word bursts and used as-is."*

Original C-ROM byte order:
```
C2 C2 C1 C1 C2 C2 C1 C1...
```

Reorganized bitplane order:
```
0 1 2 3 0 1 2 3...
```

**Result**: Complete 16-pixel line = 64 bits = four 16-bit SDRAM words, readable in a single burst.

### Original Neo Geo Sprite Format

From the NeoGeo Development Wiki:

- Sprites are 16×16 pixel tiles, 4 bits per pixel (16 colors)
- Stored as 4× 8×8 pixel blocks
- Each row stored backwards in 4-bit planar organization
- **Bitplanes split across ROM pairs**:
  - Odd C-ROMs (C1, C3, C5, C7): Bitplanes 0 and 1
  - Even C-ROMs (C2, C4, C6, C8): Bitplanes 2 and 3

This split across ROM pairs is why original hardware has **two parallel data buses** for C-ROM — both halves are read simultaneously.

### Implications for Flash Cart Design

**Option A: Store data in original format**
- Requires two separate memory reads per tile line
- Must meet original timing (~333 ns per read)
- Simpler loading, complex real-time access

**Option B: Reorganize data (MiSTer approach)**
- Single burst read for complete tile line
- Relaxed timing requirements (burst-friendly)
- Complex loading, simpler real-time access
- **Enables use of cheaper SDRAM**

**Option C: Hybrid approach**
- Store in optimized format
- Prefetch into small cache
- Serve from cache at full speed

### Custom ROM Format Proposal

For a low-cost flash cart, we could define a custom ROM format optimized for SDRAM burst access.

#### Proposed Format: `.ngfc` (Neo Geo Flash Cart)

```
Header (64 bytes):
  Offset 0x00: Magic number "NGFC" (4 bytes)
  Offset 0x04: Version (2 bytes)
  Offset 0x06: Flags (2 bytes) - encryption, region, etc.
  Offset 0x08: NGH number (4 bytes)
  Offset 0x0C: PSize (4 bytes) - Program ROM size
  Offset 0x10: SSize (4 bytes) - Fix layer size
  Offset 0x14: MSize (4 bytes) - Z80 program size  
  Offset 0x18: VSize (4 bytes) - Combined ADPCM size
  Offset 0x1C: CSize (4 bytes) - Sprite data size (after transformation)
  Offset 0x20: Original CSize (4 bytes) - For verification
  Offset 0x24: CRC32 (4 bytes)
  Offset 0x28: Reserved (24 bytes)

Data sections (in order):
  P-ROM: Original format (CPU timing is relaxed)
  S-ROM: Line-major reorganization (MiSTer algorithm)
  M-ROM: Original format (Z80 timing is relaxed)
  V-ROM: Original format (audio is buffered)
  C-ROM: **SDRAM-optimized format** (see below)
```

#### C-ROM Transformation Algorithm

Based on MiSTer's `neogeo_loader.cpp`:

```c
// Step 1: Interleave C1/C2 ROM pairs
// Input:  Separate C1 (bitplanes 0,1) and C2 (bitplanes 2,3) files
// Output: Interleaved buffer with byte order: C2 C2 C1 C1 C2 C2 C1 C1...

void interleave_crom_pair(uint8_t* c1, uint8_t* c2, uint8_t* out, size_t size) {
    for (size_t i = 0; i < size; i += 4) {
        out[i + 0] = c2[i/2 + 0];  // C2 byte 0
        out[i + 1] = c2[i/2 + 1];  // C2 byte 1
        out[i + 2] = c1[i/2 + 0];  // C1 byte 0
        out[i + 3] = c1[i/2 + 1];  // C1 byte 1
    }
}

// Step 2: Byte swap for SDRAM word alignment
// Swaps middle two bytes of each 32-bit word

void byte_swap_crom(uint32_t* buf, size_t count) {
    for (size_t i = 0; i < count; i++) {
        buf[i] = (buf[i] & 0xFF0000FF) 
               | ((buf[i] & 0x0000FF00) << 8) 
               | ((buf[i] & 0x00FF0000) >> 8);
    }
}

// Step 3: Reorder for SDRAM burst access
// Transforms data within each 32-byte tile so a 4-word burst 
// returns pixels in hardware-expected order

void reorder_for_burst(uint8_t* in, uint8_t* out, size_t size) {
    for (size_t i = 0; i < size; i++) {
        size_t j = (i & ~0x1F)                    // Keep tile boundary (bits 31:5)
                 | ((i >> 2) & 7)                 // Shift bits 4:2 → 2:0
                 | ((i & 1) << 3)                 // Move bit 0 → 3
                 | (((i & 2) << 3) ^ 0x10);       // Move bit 1 → 4, XOR with 0x10
        out[j] = in[i];
    }
}
```

#### S-ROM Transformation Algorithm

```c
// Fix layer: Convert column-major to line-major for burst reads
// Original: column 2, column 3, column 0, column 1 (each 8 lines)
// Output:   line 0 cols 0-3, line 1 cols 0-3, etc.

void transform_srom(uint8_t* in, uint8_t* out, size_t size) {
    // Each tile is 32 bytes (8x8 pixels, 4bpp, 2 bytes per row pair)
    for (size_t tile = 0; tile < size / 32; tile++) {
        uint8_t* src = &in[tile * 32];
        uint8_t* dst = &out[tile * 32];
        
        // Remap byte order within tile
        static const uint8_t remap[32] = {
            0x10, 0x18, 0x00, 0x08, 0x11, 0x19, 0x01, 0x09,
            0x12, 0x1A, 0x02, 0x0A, 0x13, 0x1B, 0x03, 0x0B,
            0x14, 0x1C, 0x04, 0x0C, 0x15, 0x1D, 0x05, 0x0D,
            0x16, 0x1E, 0x06, 0x0E, 0x17, 0x1F, 0x07, 0x0F
        };
        
        for (int i = 0; i < 32; i++) {
            dst[i] = src[remap[i]];
        }
    }
}
```

#### Conversion Tool Pseudocode

```python
def convert_to_ngfc(input_path, output_path):
    # Load standard ROMs (MAME or .neo format)
    p_rom = load_prom(input_path)
    s_rom = load_srom(input_path)
    m_rom = load_mrom(input_path)
    v_rom = load_vrom(input_path)
    c_roms = load_crom_pairs(input_path)  # List of (c1, c2) pairs
    
    # Transform S-ROM for burst access
    s_rom_transformed = transform_srom(s_rom)
    
    # Transform and interleave C-ROM pairs
    c_rom_combined = bytearray()
    for c1, c2 in c_roms:
        interleaved = interleave_crom_pair(c1, c2)
        byte_swapped = byte_swap_crom(interleaved)
        burst_ordered = reorder_for_burst(byte_swapped)
        c_rom_combined.extend(burst_ordered)
    
    # Build header
    header = build_ngfc_header(
        p_size=len(p_rom),
        s_size=len(s_rom_transformed),
        m_size=len(m_rom),
        v_size=len(v_rom),
        c_size=len(c_rom_combined),
        original_c_size=sum(len(c1)+len(c2) for c1,c2 in c_roms)
    )
    
    # Write output file
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(p_rom)
        f.write(s_rom_transformed)
        f.write(m_rom)
        f.write(v_rom)
        f.write(c_rom_combined)
```

#### Benefits of Pre-Transformed Format

1. **Zero runtime transformation** — Flash cart loader simply streams data to SDRAM
2. **Faster load times** — No CPU cycles spent on bit manipulation
3. **Simpler FPGA logic** — Data arrives ready-to-use
4. **Validated once** — Transformation correctness verified by converter tool

#### Compatibility Notes

- The transformation is **reversible** — original data can be reconstructed
- Games with encryption (CMC, SMA) must be **decrypted first** before transformation
- Largest games (Garou, KOF2002) will produce ~90+ MB transformed files
- SD card must be formatted with cluster size >= 32KB for optimal sequential read

A conversion tool would transform standard .neo or MAME ROM sets into this optimized format during PC-side preparation.

---

## References

### Project Documentation
- `docs/architecture-three-pico.md` — NeoPico-Cart implementation design
- `docs/neogeo-mvs-cartridge-reference.md` — MVS hardware pinout and timing
- `docs/neopico-cart-rp2350-feasibility.md` — RP2350 feasibility study
- `docs/transcript.txt` — VCF SoCal 2025 Talk transcript (Evie Salomon, BackBit)
- `ngfc/README.md` — NGFC format specification

### External Resources
- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [BackBit Store](https://store.backbit.io/product/backbit-platinum-mvs/)
- [MiSTer Neo Geo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [Furrtek's DEV_NOTES.md](https://github.com/MiSTer-devel/NeoGeo_MiSTer/blob/master/DEV_NOTES.md)
- [SDRAM Controller Tutorial](https://retroramblings.net/?p=1635)
- [TerraOnion NeoBuilder Guide](https://wiki.terraonion.com/index.php/Neobuilder_Guide)
- [neosdconv tool](https://github.com/city41/neosdconv)
- Alliance Memory SRAM Datasheets (AS6C8008 series)

---

## Document History

- **2024-12-13**: Initial compilation of research findings
- **2024-12-13**: Added ROM format analysis (NeoSD .neo format, MiSTer reorganization, custom format proposal)
- **2024-12-13**: Added detailed MiSTer source code analysis including exact transformation algorithms from `neogeo_loader.cpp`
- **2024-12-23**: **MAJOR CORRECTION**: Updated BackBit architecture based on Evie's VCF SoCal 2025 presentation transcript. Key findings:
  - BackBit uses PSRAM for ALL ROMs including C-ROM (not 10ns parallel SRAM)
  - **No FPGA caching required** — PSRAM connects directly to Neo Geo data bus
  - FPGA handles addressing only, not data path
  - 2× iCE40 FPGAs (flat-pack), 8× PSRAM chips for C-ROM
  - This dramatically simplifies the architecture vs. SDRAM+prefetch approaches
- Based on analysis of BackBit Platinum MVS architecture, MiSTer FPGA Neo Geo core, TerraOnion NeoSD, and original MiSTer source code
