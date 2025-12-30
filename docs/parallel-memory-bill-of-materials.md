# Parallel Memory Bill of Materials (BOM)

This document lists the specific **Parallel (Asynchronous) PSRAM and SRAM** chips required for a Direct Access architecture where the Neo Geo addresses memory directly via level shifters.

## 1. Memory Chip Requirements

These chips are selected for their asynchronous parallel interface, matching the "True Direct" addressing model. All parts are **3.3V** and require level shifting for the 5V Neo Geo bus.

| ROM Bus   | Target Size | Recommended Part | Manufacturer | Type  | Interface    | Est. Price  |
| :-------- | :---------- | :--------------- | :----------- | :---- | :----------- | :---------- |
| **C-ROM** | 64 MB       | **IS66WVG32M16** | ISSI         | PSRAM | 16-bit Async | $12.00      |
| **P-ROM** | 8 MB        | **IS66WVE4M16**  | ISSI         | PSRAM | 16-bit Async | $3.50       |
| **V-ROM** | 64 MB       | **IS66WVG32M16** | ISSI         | PSRAM | 16-bit Async | $12.00      |
| **S-ROM** | 1 MB        | **IS62WV10248**  | ISSI         | SRAM  | 8-bit Async  | $1.80       |
| **M-ROM** | 1 MB        | **IS62WV10248**  | ISSI         | SRAM  | 8-bit Async  | $1.80       |
| **TOTAL** | **138 MB**  |                  |              |       |              | **~$31.10** |

### Chip Notes

- **C-ROM / V-ROM**: The `IS66WVG32M16` is a 512Mb (64MB) G-series Async PSRAM. It is the highest density parallel part available.
- **P-ROM**: The `IS66WVE4M16` (64Mb/8MB) is a standard CellularRAM part used in many retro projects.
- **S/M-ROM**: At 1MB and below, high-speed Asynchronous SRAM (e.g., `IS62` series) is cheaper and faster (55ns) than PSRAM.

---

## 2. Supporting Logic (Level Shifting & Banking)

Because the RP2350 (3.3V) and PSRAM (3.3V) must interface with the Neo Geo (5V) across 80+ bits of data and address, level shifting is the primary supporting cost.

| Component           | Purpose                          | Part Example            | Quantity | Est. Cost |
| :------------------ | :------------------------------- | :---------------------- | :------- | :-------- |
| **Level Shifters**  | 5V ↔ 3.3V Translation            | SN74LVC245 / 74LVC16245 | ~20-25   | $9.00     |
| **Shift Registers** | Bank bit storage (A20+)          | 74HC595                 | 2-4      | $1.00     |
| **Bus Latches**     | Address multiplexing (if needed) | 74HC573                 | 4-8      | $2.00     |

---

## 3. Total Estimated BOM Cost

| Category                  | Cost (USD)  |
| :------------------------ | :---------- |
| Memory Chips              | ~$31.00     |
| Level Shifters            | ~$9.00      |
| Passives & Logic          | ~$5.00      |
| PCB (4-layer recommended) | ~$5.00      |
| **Grand Total**           | **~$50.00** |

_Prices are based on single-unit retail (Mouser/Digi-Key) as of Dec 2025._

---

## 4. Architectural Implications

- **Zero Data Path Latency**: Unlike Serial/Octal PSRAM, the Pico does not sit in the data path. Data is available at the speed of the silicon (~70ns).
- **Pin Count**: A parallel 64MB chip uses 41+ pins. This architecture requires external hardware (latches/shift registers) or multiple microcontrollers to manage the "Mapper" (Banking) role.
- **Bus Sniffing**: The RP2350's primary role during gameplay is watching the bus for bank-switch writes and updating the external address registers (Shift Registers).
