# NeoPico-Cart: RP2350-Based Architecture Feasibility Study

## Executive Summary

This document explores the feasibility of building a Neo Geo flash cartridge using RP2350 microcontrollers instead of (or alongside) an FPGA. The key finding is that a **cache-based architecture** — prefetching tile data from backing memory (PSRAM or SDRAM) into fast internal SRAM during horizontal blanking — makes an RP2350-only solution viable.

**Key enablers:**
1. RP2350's 520KB internal SRAM provides massive cache space (vs MiSTer's ~1KB BRAM)
2. The `.ngfc` format pre-transforms ROM data, eliminating real-time processing
3. PIO state machines offer FPGA-like determinism for bus response
4. PicoGUS project proves RP2040/RP2350 can handle real-time bus interfacing

**Update (Dec 2024):** BackBit's VCF SoCal 2025 presentation revealed they use PSRAM (not fast SRAM) for all ROMs including C-ROM, with direct bus connection. This validates PSRAM as a viable backing store option.

---

## The Core Problem

The Neo Geo's C-ROM (sprite graphics) bus has strict timing requirements:

| Parameter | Value |
|-----------|-------|
| Data valid window | <250ns (~8 mclk window) |
| PCK1B period | ~666ns (16 mclk at 24MHz) |
| C-ROM reads per PCK1B | 2 reads (8 mclk/~333ns each) |
| Worst-case tiles per scanline | ~96 |
| Total C-ROM size (largest games) | ~86MB (Garou: Mark of the Wolves) |

The question: **Can an RP2350 serve data fast enough?**

**Note:** Earlier versions of this document incorrectly stated ~40-60ns. The actual requirement per the NeoGeo Dev Wiki is <250ns, which makes direct PSRAM serving (like BackBit) viable.

---

## The .ngfc Format: Why It Matters

The `.ngfc` (Neo Geo Flash Cart) format pre-transforms ROM data on your PC, which is **critical** for an RP2350-only solution.

### Without Pre-Transformation (Original ROM Format)

```
To serve one 16-pixel tile line at runtime:
1. Read from C1 file (bitplanes 0,1)
2. Read from C2 file (bitplanes 2,3)
3. Interleave bytes: C2 C2 C1 C1 C2 C2 C1 C1...
4. Byte swap: [B3][B2][B1][B0] → [B3][B1][B2][B0]
5. Permute within 32-byte blocks (complex bit manipulation)
6. Output to bus

→ Burns CPU cycles, adds latency, probably impossible at Neo Geo speeds
```

### With .ngfc Pre-Transformation

```
To serve one 16-pixel tile line at runtime:
1. Copy 8 bytes from cache to bus

→ Simple memcpy, PIO-friendly, no math
```

### How It Enables RP2350

| Task | Without .ngfc | With .ngfc |
|------|---------------|------------|
| Prefetch | Complex interleaving | Sequential copy |
| Cache management | Must track bitplane pairs | Simple byte ranges |
| Bus response | Real-time transformation | Direct output |
| CPU overhead | High | Minimal |

The transformation algorithms are complex (see `ngfc/ngfc_converter.py`), but they run **once** on your PC — not 15,000 times per second on the microcontroller.

**See also:** `ngfc/README.md` for format specification and usage.

---

## BackBit's Revelation: PSRAM Works Directly

**Source:** Evie Salomon's VCF SoCal 2025 presentation (transcript in `docs/transcript.txt`)

BackBit's commercial Neo Geo flash cart uses a simpler architecture than expected:

```
BackBit Architecture:
┌─────────────────────────────────────────────────────────┐
│  Neo Geo Bus ←──── PSRAM Data Lines (direct connection) │
│       ↑                                                  │
│       │ Address                                          │
│       ↓                                                  │
│  FPGA (address translation/banking only)                │
│       ↑                                                  │
│       │ Control                                          │
│       ↓                                                  │
│  STM32 (SD card, menu, loading only)                    │
└─────────────────────────────────────────────────────────┘
```

**Key findings:**
- PSRAM serves data **directly** to Neo Geo — no FPGA in data path
- FPGA handles **addressing only** (banking, decoding)
- No BRAM caching or prefetch — PSRAM is fast enough as-is
- 8× PSRAM chips for 64MB C-ROM

**Why this matters for RP2350:**
- Validates PSRAM as backing store (simpler than SDRAM)
- But: FPGA does combinatorial address translation (~nanoseconds)
- RP2350 PIO is sequential (~cycles), so we still need the cache approach
- However, PSRAM + cache may be simpler than SDRAM + cache

---

## Why FPGAs Are Traditionally Used

FPGAs (like those in MiSTer and BackBit) offer:

- Unlimited parallel state machines
- Combinatorial logic (zero-cycle response)
- Proven SDRAM/PSRAM controllers
- Perfect determinism

However, the RP2350's PIO subsystem shares many of these properties:

| Aspect | FPGA | RP2350 PIO |
|--------|------|------------|
| Parallel state machines | Unlimited | 12 (4 per PIO block × 3 blocks) |
| Determinism | Perfect | Perfect |
| Clock speed | ~100-200MHz typical | Up to 300MHz+ overclocked |
| Pin toggle rate | Every clock edge | Every clock edge |
| Cost | $5-50 | ~$1 |

---

## The MiSTer Approach: Prefetch + Cache

MiSTer's Neo Geo core doesn't serve the bus directly from SDRAM. Instead:

```
┌─────────────────────────────────────────────────────────────┐
│                     FPGA                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            BRAM Tile Cache                          │   │
│  │            ~512-1024 bytes                          │   │
│  │            Access time: ~8ns (1 FPGA clock)         │   │
│  └─────────────────────────────────────────────────────┘   │
│         ▲                              │                    │
│         │ Prefetch during              │ Serve during       │
│         │ H-blank (~15μs)              │ active render      │
│         │                              ▼                    │
│  ┌──────┴──────────────┐    ┌─────────────────────────┐    │
│  │  SDRAM Controller   │    │   Neo Geo Bus Interface │    │
│  │  Bank interleaved   │    │   Directly from BRAM    │    │
│  │  ~40-50ns/access    │    │   ~8ns response         │    │
│  └─────────────────────┘    └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Timing Budget

```
Timeline for one scanline (~64μs total):
├─────────────────────┼──────────────────────────────────────┤
│  H-Blank (~15μs)    │  Active rendering (~49μs)            │
│                     │                                      │
│  LSPC evaluates     │  PCK1B fires, needs data             │
│  sprites            │  within <250ns                       │
│                     │                                      │
│  Prefetch tiles     │  Served from cache or PSRAM          │
│  from SDRAM→BRAM    │                                      │
└─────────────────────┴──────────────────────────────────────┘

Prefetch math:
- 96 tiles × ~50ns SDRAM = 4,800ns needed
- 15,000ns H-blank available
- Margin: 3× headroom
```

**Key insight**: With <250ns requirement, PSRAM (55ns access) can serve directly. Cache architecture still useful for simplifying logic and handling edge cases.

---

## The RP2350 Advantage: Massive Cache

MiSTer's FPGA has limited BRAM (~1-2KB for tile cache). The RP2350 has **520KB of internal SRAM**.

| Cache size | What it holds | RP2350 feasibility |
|------------|---------------|-------------------|
| 1 scanline | ~6KB (96 tiles × 64 bytes) | Easy — 1.2% of SRAM |
| 10 scanlines | ~60KB | Easy — 12% of SRAM |
| Full frame | ~150KB | Possible — 29% of SRAM |
| All of above + code | ~200KB | Still 300KB+ free |

More cache = more tolerance for SDRAM timing variation.

---

## Proposed RP2350 Architecture

### Two Separate Timing Domains

| Domain | Timing Requirement | What Handles It |
|--------|-------------------|-----------------|
| SDRAM access | Relaxed (~15μs window) | PIO + DMA, background |
| Neo Geo bus | <250ns (comfortable with PSRAM) | PIO from internal SRAM or direct PSRAM |

### Single RP2350B Design (If Pins Allow)

```
┌─────────────────────────────────────────────────────────────┐
│                      RP2350B @ 300MHz                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Internal SRAM (520KB)                  │   │
│  │                                                     │   │
│  │   ┌─────────────┐        ┌─────────────────────┐   │   │
│  │   │ Tile Cache  │        │ Code + Buffers      │   │   │
│  │   │ ~64-128KB   │        │ ~300KB+             │   │   │
│  │   │ Double-buf  │        │                     │   │   │
│  │   └─────────────┘        └─────────────────────┘   │   │
│  └──────────▲──────────────────────────│──────────────┘   │
│             │                          │                   │
│             │ DMA prefetch             │ PIO read          │
│             │ (background)             │ (real-time)       │
│             │                          ▼                   │
│  ┌──────────┴──────────┐    ┌─────────────────────────┐   │
│  │  PIO Block 0        │    │  PIO Block 1 + 2        │   │
│  │  SDRAM Controller   │    │  Neo Geo Bus Interface  │   │
│  │  ~20 pins           │    │  C/P/S/M/V ROM buses    │   │
│  └─────────────────────┘    └─────────────────────────┘   │
│             │                          │                   │
└─────────────┼──────────────────────────┼───────────────────┘
              ▼                          ▼
        ┌──────────┐              ┌──────────────┐
        │  SDRAM   │              │  Neo Geo     │
        │  128MB   │              │  Cartridge   │
        │          │              │  Bus         │
        └──────────┘              └──────────────┘
```

### Dual RP2350B Design (Pin-Constrained)

```
┌─────────────────────────────────────────────────────────────┐
│                 Pico A: "Memory Server"                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PIO: SDRAM Controller                              │   │
│  │  DMA: Burst reads into buffer                       │   │
│  │  Core 0: Prefetch scheduling                        │   │
│  │  Core 1: Inter-Pico communication                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ High-speed parallel link
                          │ (PIO, 16-bit @ 150MHz+)
┌─────────────────────────┴───────────────────────────────────┐
│                 Pico B: "Bus Interface"                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Internal SRAM: Tile cache (double-buffered)        │   │
│  │  PIO 0: C-ROM bus interface                         │   │
│  │  PIO 1+2: P/S/M/V bus interfaces                    │   │
│  │  Core 0: Cache management                           │   │
│  │  Core 1: Real-time coordination                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## SDRAM Protocol Overview

SDRAM is organized as banks × rows × columns:

- **Banks** (2-4): Independent sheets, can pipeline accesses
- **Rows** (thousands): Opening a row is slow (~20ns)
- **Columns** (hundreds): Once row is open, column access is fast

### Key Commands

| RAS# | CAS# | WE# | Command |
|------|------|-----|---------|
| 0 | 1 | 1 | ACTIVATE (open a row) |
| 1 | 0 | 1 | READ |
| 1 | 0 | 0 | WRITE |
| 0 | 1 | 0 | PRECHARGE (close a row) |
| 0 | 0 | 0 | AUTO REFRESH |

### Typical Read Sequence

```
T0    ACTIVATE     Row address    -         "Open row 1234"
T1    NOP          -              -         Wait (tRCD ~20ns)
T2    NOP          -              -         
T3    READ         Column addr    -         "Read column 56"
T4    NOP          -              -         Wait (CAS latency)
T5    NOP          -              -         
T6    -            -              DATA0     First word arrives
T7    -            -              DATA1     Burst continues
T8    -            -              DATA2     
T9    -            -              DATA3     Burst complete
```

### Why .ngfc Format Helps

Pre-transformed ROM data means burst reads return data in the exact order needed:

- Original C-ROM: Bitplanes split across ROM pairs, complex interleaving
- Transformed: Complete 64-bit tile line in 4 consecutive 16-bit words
- Result: One burst read = one tile line, no CPU transformation needed

---

## Backing Store: PSRAM vs SDRAM

Both memory types can work with the cache-based architecture. Here's the tradeoff:

### PSRAM (Pseudo-Static RAM)

**Pros:**
- Simple SRAM-like interface (no command sequences)
- No refresh management
- Easier PIO implementation
- Proven by BackBit for Neo Geo
- No high-speed PCB design needed (<50 MHz)

**Cons:**
- More expensive per MB (~$5-8 per 64Mbit chip)
- Need ~10 chips for full 128MB capacity
- Lower density than SDRAM

**Typical parts:** APMemory APS6404L (64Mbit QSPI), ESP-PSRAM64H

### SDRAM (Synchronous Dynamic RAM)

**Pros:**
- Cheaper per MB (~$5-10 for 512Mbit chip)
- Single chip for 64-128MB
- Well-documented (MiSTer uses this)
- Higher burst throughput

**Cons:**
- Complex protocol (ACTIVATE, READ, PRECHARGE, REFRESH)
- Needs high-speed PCB design (100-144 MHz)
- More complex PIO implementation
- Refresh cycles steal bandwidth

### Recommendation for RP2350

**Start with PSRAM** because:
1. Simpler PIO code to get working
2. BackBit proves it works for Neo Geo specifically
3. Can always "cost reduce" to SDRAM later (Evie mentioned this in her talk)
4. Focus on proving the cache architecture first

```
Development path:
PSRAM (simple, proven) → Get it working → Optimize → SDRAM (optional cost reduction)
```

---

## Prior Art: PicoGUS

The PicoGUS project proves RP2040 + PIO can handle real-time bus interfacing:

- **Hardware**: RP2040 + 8MB SPI PSRAM
- **Bus**: ISA bus (similar timing constraints to Neo Geo)
- **Approach**: Custom PIO code for bus interface + high-speed PSRAM access
- **Clock**: Runs at 280-400MHz overclocked
- **Result**: Successfully emulates Gravis Ultrasound, Sound Blaster, etc.

Key quote from the creator:
> "I've created PIO code to handle the ISA bus and interface with SPI-based PSRAM at higher speed than I could with the RP2040's built-in SPI peripheral"

### What PicoGUS Demonstrates

1. PIO can react to external bus events in real-time
2. External memory (PSRAM) can be accessed fast enough via PIO
3. Overclocking to 300MHz+ is stable and practical
4. DMA keeps CPU free for other tasks

---

## XMOS lib_sdram Reference

XMOS implements a software-driven parallel SDRAM controller:

- **Interface**: 16-bit SDR SDRAM at up to 62.5MHz
- **Pin count**: Only 20 pins (address/data overlaid)
- **Approach**: Deterministic multi-core execution

If XMOS can do software SDRAM at 62.5MHz, PIO at 150-300MHz should exceed this.

---

## Comparison: Option A vs Option B

### Option A: RP2350B + FPGA

| Component | Role |
|-----------|------|
| RP2350B | SD card, menu, loads ROM into SDRAM |
| FPGA | SDRAM controller, all bus interfaces |

**Pros**: Proven, FPGA handles all timing-critical paths  
**Cons**: Higher cost, more complexity, two different toolchains

### Option B: Dual RP2350B (No FPGA)

| Component | Role |
|-----------|------|
| RP2350B #1 | SDRAM controller, prefetch engine |
| RP2350B #2 | All Neo Geo bus interfaces, tile cache |

**Pros**: Lower cost, single toolchain, pushes Pico to its limits  
**Cons**: Unproven for this specific application, needs experimentation

---

## Key Insights

### 1. Cache Architecture Eliminates Timing Concerns

By prefetching into internal SRAM during H-blank, SDRAM access timing becomes irrelevant to bus response timing. Two completely decoupled domains.

### 2. RP2350's 520KB SRAM Is Huge

MiSTer's FPGA has ~1KB BRAM for tile cache. RP2350 has 500× more. This provides massive margin for timing variations and simplifies cache management.

### 3. PIO Is Deterministic Like an FPGA

PIO state machines execute one instruction per clock with zero jitter. For real-time bus response, they're functionally equivalent to FPGA logic.

### 4. The Hard Problem Is Already Solved

MiSTer's Neo Geo core proves the prefetch + cache architecture works. The .ngfc format (pre-transformed ROMs) is already defined. What's left is implementation.

### 5. Prior Art Exists

PicoGUS proves RP2040/RP2350 can handle real-time bus interfacing with external memory. The techniques are transferable.

---

## Recommended Next Steps

### Phase 1: Validate Core Assumptions

1. **Build a PIO SDRAM controller**
   - Target: 62.5-100MHz clock, burst reads working
   - Reference: XMOS lib_sdram architecture
   - Measure: Actual latency per burst read

2. **Test internal SRAM access speed**
   - Benchmark: PIO reading from SRAM → outputting to pins
   - Target: <20ns from trigger to data valid

3. **Prototype Neo Geo bus sniffer**
   - Capture actual PCK1B timing on real hardware
   - Measure address-to-data timing requirements
   - Validate <250ns requirement and measure actual margins

### Phase 2: Proof of Concept

1. **Single-game demo**
   - Load one game's .ngfc data into SDRAM at boot
   - Implement prefetch + cache for C-ROM only
   - P/S/M/V can use simpler (slower) approach initially

2. **Timing validation**
   - Run on real Neo Geo hardware
   - Check for visual glitches (cache misses)
   - Profile cache hit rate

### Phase 3: Full Implementation

1. **Complete bus implementation** (all ROM types)
2. **SD card loading and menu system**
3. **PCB design and integration**

---

## Cost Comparison

| Approach | Key Components | Estimated BOM |
|----------|---------------|---------------|
| BackBit (PSRAM + FPGA) | ~10× PSRAM + 2× iCE40 + STM32 | ~$100-200 |
| FPGA + SDRAM | ECP5/Gowin + SDRAM + RP2350 | ~$50-100 |
| RP2350 + PSRAM | 1-2× RP2350B + PSRAM | ~$40-70 |
| RP2350 + SDRAM | 1-2× RP2350B + SDRAM | ~$30-50 |

**Note:** BackBit's actual BOM is much lower than previously estimated (was wrongly assumed to use expensive 10ns SRAM). The RP2350 approach is cost-competitive with commercial solutions while being simpler to develop.

---

## Conclusion

A multi-RP2350 Neo Geo flash cartridge appears **feasible** based on:

1. The cache architecture decouples backing store timing from bus response timing
2. RP2350's 520KB SRAM provides ample cache space (500× more than MiSTer's BRAM)
3. PIO offers FPGA-like determinism for bus interfaces
4. PicoGUS demonstrates the approach works for similar applications
5. The `.ngfc` format eliminates real-time data transformation
6. **BackBit proves PSRAM works for Neo Geo** — validates our backing store choice

The main risks:
- Uncharted territory for PIO-based memory controllers
- Pin count constraints require multi-Pico design (3× RP2350)
- Six-slot MVS machines have tighter timing (may need optimization)

But the physics work out, BackBit proves the concept, and the potential cost/simplicity benefits justify experimentation.

## Concrete Implementation

Based on this feasibility analysis, a concrete architecture has been designed:

**See: `docs/architecture-three-pico.md`**

The "Triple Pico" architecture uses:
- **Pico A (Master):** SD card, menu, P-ROM, V-ROM
- **Pico B (C-ROM):** Timing-critical sprite graphics
- **Pico C (S/M-ROM):** Fix layer and Z80 program

This design follows BackBit's approach (PSRAM direct to Neo Geo, controller handles addressing only) but replaces the FPGA with RP2350 PIO.

---

## References

### Project Documentation
- `docs/architecture-three-pico.md` — **Concrete implementation design**
- `docs/neogeo-mvs-cartridge-reference.md` — MVS hardware reference (pinout, timing)
- `docs/neogeo-flashcart-research.md` — Flash cart analysis, BackBit/MiSTer
- `docs/transcript.txt` — Evie Salomon's VCF SoCal 2025 presentation transcript
- `ngfc/README.md` — NGFC format specification and converter tool

### External Resources
- [MiSTer Neo Geo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- [PicoGUS Project](https://github.com/polpo/picogus)
- [rp2040-psram Library](https://github.com/polpo/rp2040-psram)
- [XMOS lib_sdram](https://github.com/xmos/lib_sdram)
- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [RP2350 Datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)
- [BackBit Store](https://store.backbit.io/product/backbit-platinum-mvs/)

---

*Document created: December 2024*
*Updated: December 2024 — Added BackBit PSRAM findings, .ngfc integration, PSRAM vs SDRAM comparison*
