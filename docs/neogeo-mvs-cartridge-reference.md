# Neo Geo MVS Cartridge Hardware Reference

A comprehensive technical reference for the Neo Geo MVS cartridge interface, covering pinouts, buses, timing, and signal specifications.

**Sources:** [NeoGeo Development Wiki](https://wiki.neogeodev.org/), [Jamma Nation X](http://www.jamma-nation-x.com/jammax/mvspinout.html), various schematics and community documentation.

---

## Table of Contents

1. [Physical Specifications](#physical-specifications)
2. [Board Structure](#board-structure)
3. [System Clocks](#system-clocks)
4. [ROM Types Overview](#rom-types-overview)
5. [P-ROM Bus (Program)](#p-rom-bus-program)
6. [C-ROM Bus (Sprites)](#c-rom-bus-sprites)
7. [S-ROM Bus (Fix Layer)](#s-rom-bus-fix-layer)
8. [M-ROM Bus (Z80)](#m-rom-bus-z80)
9. [V-ROM Bus (Audio)](#v-rom-bus-audio)
10. [Display Timing](#display-timing)
11. [Sprite Rendering Pipeline](#sprite-rendering-pipeline)
12. [Cartridge Pinout](#cartridge-pinout)
13. [Key Chips Reference](#key-chips-reference)
14. [Voltage and Electrical](#voltage-and-electrical)

---

## Physical Specifications

| Parameter | Value |
|-----------|-------|
| Pin pitch | 0.1 inch (2.54mm) |
| Board thickness | 1.6mm |
| Pins per board | 120 (60 per side) |
| Total pins per cartridge | 240 |
| Connector type | Card edge |
| Board count | 2 (PROG + CHA) |

---

## Board Structure

The Neo Geo cartridge consists of two separate PCBs connected via internal ribbon cables:

### CHA Board (Bottom - CTRG1)

**Purpose:** Character/graphics data

| Contents | Description |
|----------|-------------|
| C-ROM | Sprite graphics (16-bit pairs) |
| S-ROM | Fix layer graphics (8-bit) |
| M-ROM | Z80 program code (8-bit) |
| NEO-ZMC2 / PRO-CT0 | C-ROM serializer (on some boards) |

### PROG Board (Top - CTRG2)

**Purpose:** Program code and audio samples

| Contents | Description |
|----------|-------------|
| P-ROM | 68000 program code (16-bit) |
| V-ROM | ADPCM audio samples |
| Banking logic | For games > 1MB P-ROM |

### Common Board Types

| PROG Board | CHA Board | Max C-ROM | Notes |
|------------|-----------|-----------|-------|
| PROG-B | CHA-32 | 4MB | Early small games |
| PROG-B | CHA-42 | 8MB | Common mid-era |
| PROGBK1 | CHA256 | 32MB | Large games |
| PROGBK1 | CHA512Y | 64MB | Maximum capacity |

**Note:** Later boards (post-1999) may include encryption chips (NEO-CMC, NEO-SMA).

---

## System Clocks

All timing derives from a master crystal oscillator:

| Signal | Frequency | Derivation | Generator | Purpose |
|--------|-----------|------------|-----------|---------|
| **24M** | 24.000 MHz (MVS) / 24.167829 MHz (AES) | Master clock | Crystal | Reference |
| **12M** | 12 MHz | 24M ÷ 2 | NEO-D0 | 68000 CPU, NEO-ZMC2 |
| **8M** | 8 MHz | 24M ÷ 3 | LSPC2-A2 | YM2610 sound chip |
| **6M** | 6 MHz | 24M ÷ 4 | NEO-D0 | Pixel clock, video output |
| **4M** | 4 MHz | 24M ÷ 6 | LSPC2-A2 | Z80 CPU |
| **3M** | 3 MHz | 24M ÷ 8 | NEO-D0 | NEO-B1 |
| **68KCLK** | 12 MHz | = 12M | NEO-D0 | 68000 clock input |

**1 mclk (master clock cycle) = 41.67 ns**

**1 pixel = 4 mclk = 166.67 ns**

---

## ROM Types Overview

| ROM Type | Bus Width | Max Size | Timing Requirement | Purpose |
|----------|-----------|----------|-------------------|---------|
| P-ROM | 16-bit | 2MB+ (banked) | 150ns | 68000 program |
| C-ROM | 32-bit (2×16) | 64MB+ | <250ns (7 mclk) | Sprite graphics |
| S-ROM | 8-bit | 128KB+ | ~200ns (5-6 mclk, uncertain) | Fix layer graphics |
| M-ROM | 8-bit | 128KB+ | Relaxed | Z80 program |
| V-ROM | 8-bit | 32MB+ | A: >2μs, B: 250ns | ADPCM samples |

---

## P-ROM Bus (Program)

### Overview

The P-ROM contains 68000 machine code. It connects to the main CPU data and address buses.

### Specifications

| Parameter | Value |
|-----------|-------|
| Data bus width | 16 bits (D0-D15) |
| Address bus | A1-A19 (directly addressable: 1MB) |
| Minimum speed | 150ns |
| Access type | Asynchronous with /DTACK |

### Memory Map

| Address Range | Size | Description |
|---------------|------|-------------|
| $000000-$0FFFFF | 1MB | P-ROM (directly mapped) |
| $200000-$2FFFFF | 1MB | P-ROM bank window (if banked) |

### Banking

Games larger than 1MB use bank switching:
- Banks are typically 1MB each
- Controlled by writes to specific addresses
- Some games use NEO-SMA for banking + encryption

**Note:** For 2MB P-ROM, mapping is inverted: second 1MB at $000000, first 1MB at $200000.

### Control Signals

| Signal | Description |
|--------|-------------|
| /ROMOE | P1 ROM output enable |
| /ROMOEL | P ROM lower byte enable |
| /ROMOEU | P ROM upper byte enable |
| /DTACK | Data acknowledge to CPU |
| R/W | Read/Write direction |
| AS | Address strobe |

---

## C-ROM Bus (Sprites)

### Overview

The C-ROM bus is the most timing-critical. It feeds sprite graphics data to the video pipeline for real-time rendering.

### Specifications

| Parameter | Value |
|-----------|-------|
| Data bus width | 32 bits (CR0-CR31) |
| Organization | Paired 16-bit ROMs (odd/even) |
| Max capacity | 64MB+ (with banking) |
| Timing requirement | <250ns (7 mclk) |
| Tiles per scanline | Max 96 |

### ROM Pairing

C-ROMs are organized in pairs, each containing half the bitplanes:

| ROM | Contains | Bitplanes |
|-----|----------|-----------|
| Odd (C1, C3, C5...) | First half | 0, 1 |
| Even (C2, C4, C6...) | Second half | 2, 3 |

Both ROMs are read simultaneously, providing 32 bits (4 bytes) per access.

### Address Latching

C-ROM addresses are extracted from the multiplexed P-bus using latch chips:

| Signal | Function |
|--------|----------|
| **PCK1B** | Clock to latch C-ROM address |
| P0-P23 | Multiplexed address from LSPC |
| CA4 | Separate address bit (not on P-bus) |

**PCK1B Timing:**
- Frequency: 1.5 MHz
- Low period: 55ns
- High period: 610ns
- **Total period: ~666ns (16 mclk)**

### Tile Format

Sprites are 16×16 pixels, 4 bits per pixel (16 colors):

```
Tile structure: 128 bytes total
├── 4 quadrants of 8×8 pixels each
├── Each quadrant: 32 bytes
├── Rows stored backwards within quadrant
└── Bitplanes split across ROM pairs
```

### Serialization

The 32-bit parallel data must be serialized to 4-bit pixels:

| Chip | Location | Function |
|------|----------|----------|
| NEO-ZMC2 | Motherboard (AES) or CHA board | Serializes C-ROM data |
| PRO-CT0 | CHA board variant | Alternative serializer |
| NEO-CMC | CHA board (late games) | Serializer + encryption |

**NEO-ZMC2 Timing:**
- Clock: 12 MHz
- Latches data on rising edge of 12M
- Outputs next pixel on falling edge

---

## S-ROM Bus (Fix Layer)

### Overview

The S-ROM contains the "fix" layer - static text/UI graphics that overlay sprites.

### Specifications

| Parameter | Value |
|-----------|-------|
| Data bus width | 8 bits (FIXD0-FIXD7) |
| Max capacity | 128KB (banked with NEO-CMC) |
| Timing requirement | ~200ns (5-6 mclk, uncertain) |
| Tile size | 8×8 pixels, 4bpp |

### Tile Format

Fix tiles are 8×8 pixels, 4 bits per pixel:

```
Storage: 32 bytes per tile
├── Pixels coded in pairs as bytes
├── Stored in columns (top to bottom)
├── Pixel order swapped within byte:
│   └── Left pixel: bits 0-3
│   └── Right pixel: bits 4-7
└── Column order: mixed (not linear)
```

### Address Format

```
Address bits: ...nHCLLL
├── n: Tile number
├── H: Half (0=right, 1=left)
├── C: Column within half
└── L: Line number (0-7)
```

### Address Latching

| Signal | Function |
|--------|----------|
| **PCK2B** | Clock to latch S-ROM address |
| 2H1 | Separate address bit (SA3) |

---

## M-ROM Bus (Z80)

### Overview

The M-ROM contains the Z80 sound CPU program code.

### Specifications

| Parameter | Value |
|-----------|-------|
| Data bus width | 8 bits (SDD0-SDD7) |
| Address bus | 16 bits (SDA0-SDA15) |
| Max capacity | 128KB (64KB directly + banking) |
| Timing requirement | Relaxed (Z80 @ 4MHz) |

### Banking

For M-ROM > 64KB:
- NEO-ZMC or NEO-ZMC2 handles bank switching
- Lower 32KB: Fixed
- Upper 32KB: Bankable window

### Control Signals

| Signal | Function |
|--------|----------|
| /SDMRD | M-ROM read enable |
| /SDROM | ROM chip select |

---

## V-ROM Bus (Audio)

### Overview

V-ROMs contain ADPCM audio samples for the YM2610 sound chip.

### Specifications

The YM2610 has two ADPCM channels with different timing:

| Channel | Bus Width | Timing Requirement | Typical Size |
|---------|-----------|-------------------|--------------|
| ADPCM-A | 8-bit | >2μs | Variable |
| ADPCM-B | 8-bit | 250ns | Variable |

### Address Buses

**ADPCM-A:**
- SDRAD0-SDRAD7 (multiplexed)
- SDRA8-SDRA9, SDRA20-SDRA23

**ADPCM-B:**
- SDPAD0-SDPAD7 (multiplexed)
- SDPA8-SDPA11

### Control Signals

| Signal | Function |
|--------|----------|
| /SDRD0 | ADPCM-A ROM read |
| /SDRD1 | ADPCM-B ROM read |
| /SDPOE | PCM output enable |

---

## Display Timing

### Frame Structure (NTSC)

| Parameter | Value |
|-----------|-------|
| Resolution | 320×224 visible |
| Total pixels | 384×264 |
| Frame rate | ~59.185 Hz |
| Scanline duration | 1536 mclk (64μs) |

### Horizontal Timing (per scanline)

| Phase | Duration (mclk) | Duration (px) | Duration (μs) |
|-------|-----------------|---------------|---------------|
| H-Sync | 112 | 28 | 4.67 |
| Back porch | 112 | 28 | 4.67 |
| **Active display** | 1280 | 320 | 53.33 |
| Front porch | 32 | 8 | 1.33 |
| **H-Blank total** | 256 | 64 | 10.67 |
| **Total** | 1536 | 384 | 64.00 |

### Vertical Timing (NTSC)

| Phase | Scanlines |
|-------|-----------|
| V-Sync | 8 |
| Top border | 16 (blanked) |
| **Active display** | 224 |
| Bottom border | 16 (blanked) |
| **Total** | 264 |

### Blanking Signals

| Signal | Function |
|--------|----------|
| CHBL | Horizontal blanking - forces palette 0, color 0 |
| BNKB | Vertical blanking - forces DAC to 0 |

---

## Sprite Rendering Pipeline

### Overview

The LSPC chip renders sprites using a line buffer architecture with pipelined parsing and rendering.

### Line Buffer Architecture

```
4 line buffers (160 pixels each, odd/even interleaved)
├── Buffer pair A: Rendering
└── Buffer pair B: Output to display
(Swapped each scanline)
```

Two pixels are rendered simultaneously via odd/even buffer pairs.

### Pipeline Timing

| Line N-2 | Line N-1 | Line N |
|----------|----------|--------|
| Parse sprites for N | Render sprites for N | Output line N |

### Sprite Parsing (during line N-2)

1. Read Y position of each sprite (up to 381)
2. Check if sprite visible on line N
3. Add visible sprites to active list
4. Stop when: 381 sprites parsed OR 96 sprites in list

### Sprite Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Sprites per scanline | 96 | Hardware limit |
| Sprites per frame | 381 | VRAM constraint allows 448, but parsing limited |
| Sprite priority | 1 = back, higher = front | |

### C-ROM Access Pattern

Per rendered tile line:
1. PCK1B rises → Address latched from P-bus
2. Address decoded to C-ROM
3. 32-bit data read from C-ROM pair
4. NEO-ZMC2 serializes to 2 pixels at a time
5. Pixels written to line buffer

**Timing budget per tile: ~666ns (PCK1B period)**

---

## Cartridge Pinout

### CHA Board (CTRG1) - Bottom Board

**Top Side (Component side facing up):**

| Pin | Signal | Pin | Signal |
|-----|--------|-----|--------|
| 1 | GND | 31 | CR16 |
| 2 | GND | 32 | CR17 |
| 3 | P0 | 33 | CR18 |
| 4 | P1 | 34 | CR19 |
| 5 | P2 | 35 | CR20 |
| 6 | P3 | 36 | CR21 |
| 7 | P4 | 37 | CR22 |
| 8 | P5 | 38 | CR23 |
| 9 | P6 | 39 | CR24 |
| 10 | P7 | 40 | CR25 |
| 11 | P8 | 41 | CR26 |
| 12 | P9 | 42 | CR27 |
| 13 | P10 | 43 | CR28 |
| 14 | P11 | 44 | CR29 |
| 15 | P12 | 45 | CR30 |
| 16 | P13 | 46 | CR31 |
| 17 | P14 | 47 | FIXD0 |
| 18 | P15 | 48 | FIXD1 |
| 19 | P16 | 49 | FIXD2 |
| 20 | P17 | 50 | FIXD3 |
| 21 | P18 | 51 | FIXD4 |
| 22 | P19 | 52 | FIXD5 |
| 23 | P20 | 53 | FIXD6 |
| 24 | P21 | 54 | FIXD7 |
| 25 | P22 | 55 | SDD4 |
| 26 | P23 | 56 | SDD5 |
| 27 | PCK1B | 57 | SDD6 |
| 28 | PCK2B | 58 | SDD7 |
| 29 | VCC | 59 | VCC |
| 30 | VCC | 60 | VCC |

**Bottom Side:**

| Pin | Signal | Pin | Signal |
|-----|--------|-----|--------|
| 1 | GND | 31 | CR0 |
| 2 | GND | 32 | CR1 |
| 3 | CA4 | 33 | CR2 |
| 4 | 2H1 | 34 | CR3 |
| 5 | 24M | 35 | CR4 |
| 6 | 12M | 36 | CR5 |
| 7 | 8M | 37 | CR6 |
| 8 | EVEN | 38 | CR7 |
| 9 | LOAD | 39 | CR8 |
| 10 | H | 40 | CR9 |
| 11 | RESET | 41 | CR10 |
| 12 | SDA0 | 42 | CR11 |
| 13 | SDA1 | 43 | CR12 |
| 14 | SDA2 | 44 | CR13 |
| 15 | SDA3 | 45 | CR14 |
| 16 | SDA4 | 46 | CR15 |
| 17 | SDA5 | 47 | SDA8 |
| 18 | SDA6 | 48 | SDA9 |
| 19 | SDA7 | 49 | SDA10 |
| 20 | SDA12 | 50 | SDA11 |
| 21 | SDA13 | 51 | SDRD0 |
| 22 | SDA14 | 52 | SDRD1 |
| 23 | SDA15 | 53 | SDROM |
| 24 | SDMRD | 54 | SDDO |
| 25 | SDD0 | 55 | GND |
| 26 | SDD1 | 56 | GND |
| 27 | SDD2 | 57 | GND |
| 28 | SDD3 | 58 | GND |
| 29 | VCC | 59 | VCC |
| 30 | VCC | 60 | VCC |

### PROG Board (CTRG2) - Top Board

**Top Side:**

| Pin | Signal | Pin | Signal |
|-----|--------|-----|--------|
| 1 | GND | 31 | D8 |
| 2 | GND | 32 | D9 |
| 3 | D0 | 33 | D10 |
| 4 | D1 | 34 | D11 |
| 5 | D2 | 35 | D12 |
| 6 | D3 | 36 | D13 |
| 7 | D4 | 37 | D14 |
| 8 | D5 | 38 | D15 |
| 9 | D6 | 39 | SDRA8 |
| 10 | D7 | 40 | SDRA9 |
| 11 | A1 | 41 | SDRA20 |
| 12 | A2 | 42 | SDRA21 |
| 13 | A3 | 43 | SDRA22 |
| 14 | A4 | 44 | SDRA23 |
| 15 | A5 | 45 | SDRAD0 |
| 16 | A6 | 46 | SDRAD1 |
| 17 | A7 | 47 | SDRAD2 |
| 18 | A8 | 48 | SDRAD3 |
| 19 | A9 | 49 | SDRAD4 |
| 20 | A10 | 50 | SDRAD5 |
| 21 | A11 | 51 | SDRAD6 |
| 22 | A12 | 52 | SDRAD7 |
| 23 | A13 | 53 | SDPA8 |
| 24 | A14 | 54 | SDPA9 |
| 25 | A15 | 55 | SDPA10 |
| 26 | A16 | 56 | SDPA11 |
| 27 | A17 | 57 | GND |
| 28 | A18 | 58 | GND |
| 29 | VCC | 59 | VCC |
| 30 | VCC | 60 | VCC |

**Bottom Side:**

| Pin | Signal | Pin | Signal |
|-----|--------|-----|--------|
| 1 | GND | 31 | R/W |
| 2 | GND | 32 | AS |
| 3 | A19 | 33 | /ROMOE |
| 4 | (NC) | 34 | 4MB |
| 5 | SYSTEMB | 35 | /ROMOEU |
| 6 | SLOTCS | 36 | /ROMOEL |
| 7 | /RESET | 37 | /PORTOEL |
| 8 | ROMWAIT | 38 | /PORTOEU |
| 9 | PWAIT0 | 39 | /PORTADRS |
| 10 | PWAIT1 | 40 | /PORTWE |
| 11 | PDTACK | 41 | VPA |
| 12 | SDD0 | 42 | SDPAD0 |
| 13 | SDD1 | 43 | SDPAD1 |
| 14 | SDD2 | 44 | SDPAD2 |
| 15 | SDD3 | 45 | SDPAD3 |
| 16 | SDD4 | 46 | SDPAD4 |
| 17 | SDD5 | 47 | SDPAD5 |
| 18 | SDD6 | 48 | SDPAD6 |
| 19 | SDD7 | 49 | SDPAD7 |
| 20 | /SDPOE0 | 50 | /SDPOE1 |
| 21 | /SDROE | 51 | /SDRMPX |
| 22 | /SDRA00 | 52 | /SDRMPX |
| 23 | /SDRA01 | 53 | SDRA00 |
| 24 | SDRA02 | 54 | SDRA01 |
| 25 | SDRA03 | 55 | SDRA02 |
| 26 | SDRA04 | 56 | SDRA03 |
| 27 | SDRA05 | 57 | SDRA04 |
| 28 | SDRA06 | 58 | SDRA05 |
| 29 | VCC | 59 | VCC |
| 30 | VCC | 60 | VCC |

**Note:** Original schematics had /ROMOE and 4MB swapped. Corrected pinout shown above.

---

## Key Chips Reference

### LSPC (Line Sprite Controller)

| Function | Description |
|----------|-------------|
| Sprite parsing | Evaluates which sprites visible per line |
| P-bus control | Multiplexes tile/palette data |
| Timing generation | PCK1B, PCK2B, blanking signals |
| Line buffer control | CK1-4, WE signals |

### NEO-B1

| Function | Description |
|----------|-------------|
| Line buffers | Handles sprite rendering into internal line buffers |
| Palette interface | Outputs addresses to external 4KB palette RAM |
| Color lookup | Converts tile pixels to RGB via DAC |
| Fix layer rendering | Real-time overlay on sprite buffer output |

**Note:** The 4KB palette RAM consists of external SRAM chips; NEO-B1 interfaces with but does not contain this memory.

### NEO-ZMC2 / PRO-CT0

| Function | Description |
|----------|-------------|
| C-ROM serialization | 32-bit parallel → 4-bit serial |
| Horizontal flip | Reverses pixel order |
| EVEN swap | Swaps pixel pairs |
| M-ROM banking | Address generation for Z80 |

### NEO-D0

| Function | Description |
|----------|-------------|
| Clock generation | Divides 24M to 12M (÷2), 6M (÷4), 3M (÷8) |
| Watchdog | System reset on hang (via CHBL counter) |
| Z80 control | Memory and port control, YM2610 interface |
| Memory card | Bank selection control |

**Note:** The calendar/RTC is handled by a separate D4990 chip, not NEO-D0. LSPC2-A2 generates 8M (÷3) and 4M (÷6) clocks.

### YM2610

| Function | Description |
|----------|-------------|
| Sound generation | FM synthesis + ADPCM playback |
| V-ROM interface | Dual ADPCM channels (A + B) |
| SSG | 3-channel square wave |

---

## Voltage and Electrical

### Power Rails

| Rail | Voltage | Purpose |
|------|---------|---------|
| VCC | +5V | Logic and ROMs |
| GND | 0V | Ground reference |

### Signal Levels

| Parameter | Value |
|-----------|-------|
| Logic family | 5V TTL/CMOS |
| VOH (output high) | >2.4V |
| VOL (output low) | <0.4V |
| VIH (input high) | >2.0V |
| VIL (input low) | <0.8V |

### Level Shifting Considerations

Modern components (3.3V FPGA, MCU, PSRAM) require level shifting:

| Approach | Latency | Notes |
|----------|---------|-------|
| Auto-sensing bidirectional | 8-15ns | Avoid for timing-critical signals |
| Direction-specified | 3-8ns | Preferred (e.g., TI TXB series) |
| Series resistor + clamp | <1ns | Works for some inputs |

**Critical:** Level shifter latency directly impacts timing budget.

---

## References

- [NeoGeo Development Wiki](https://wiki.neogeodev.org/)
- [Jamma Nation X MVS Pinout](http://www.jamma-nation-x.com/jammax/mvspinout.html)
- [MiSTer Neo Geo Core](https://github.com/MiSTer-devel/NeoGeo_MiSTer)
- Original SNK schematics (various sources)

---

*Document version: 1.1*
*Created: December 2025*
*Last updated: December 2025 - Fact-checked against NeoGeo Development Wiki and other sources*

### Changelog
- **v1.1**: Corrected clock generation attribution (NEO-D0 vs LSPC2-A2), clarified NEO-D0 functions (calendar is D4990, not NEO-D0), updated NEO-B1 description (palette RAM is external), noted S-ROM timing uncertainty.
