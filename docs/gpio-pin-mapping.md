# GPIO Pin Mapping

MVS Cart Edge → RP2350B GPIO assignments for neopico-cart.

## Pico A: P/V-ROM Controller

### From MVS PROG Connector (Input)
| GPIO | MVS Signal | MVS Pin | Notes |
|------|------------|---------|-------|
| 0-15 | D0-D15 | Top 3-10, 31-38 | P-ROM data (bidir) |
| 16-34 | A1-A19 | Top 11-27, Bot 3 | P-ROM address |
| 35 | /ROMOE | Bot 33 | Output enable |
| 36 | R/W | Bot 31 | Read/Write |
| 37 | SLOTCS | Bot 6 | Slot select |

### To PSRAM (Output)
| GPIO | Signal | Notes |
|------|--------|-------|
| 38-41 | QSPI_D0-D3 | PSRAM data |
| 42 | QSPI_CLK | PSRAM clock |
| 43-44 | /CS_P, /CS_V | PSRAM chip selects |

---

## Pico B: C-ROM Controller

### From MVS CHA Connector (Input)
| GPIO | MVS Signal | MVS Pin | Notes |
|------|------------|---------|-------|
| 0-7 | CA3-CA10 | Top 21-28 | C-ROM tile address |
| 8 | PCK1B | Top 7 | Pixel clock |
| 9 | EVEN/ODD | Top 6 | Line select |

### To MVS CHA Connector (Output)
| GPIO | MVS Signal | MVS Pin | Notes |
|------|------------|---------|-------|
| 10-41 | CR0-CR31 | Top 1-4 (×8 banks) | C-ROM 32-bit data out |

### To PSRAM (Output)
| GPIO | Signal | Notes |
|------|--------|-------|
| 42-47 | /CS0-CS5 | PSRAM array selects |

---

## Pico C: S/M-ROM Controller

### From MVS CHA Connector (Input)
| GPIO | MVS Signal | MVS Pin | Notes |
|------|------------|---------|-------|
| 0-11 | Fix addr | via latch | S-ROM address |
| 12 | PCK2B | Top 53 | Fix layer clock |
| 13 | /SFIX | Top 57 | S-ROM enable |

### To MVS CHA Connector (Output)
| GPIO | MVS Signal | MVS Pin | Notes |
|------|------------|---------|-------|
| 14-21 | FD0-FD7 | Top 37-44 | S-ROM data |
| 22-29 | SDA0-SDA7 | Bot 12-19 | M-ROM data (Z80 sound) |

---

*Pin assignments are preliminary. GPIO numbers will change based on PIO requirements and PCB routing.*
