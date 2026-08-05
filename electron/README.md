# ALTAIR Electron Engine

Electron is the primary financial calculation and checking engine of the ALTAIR system. It is responsible for executing real-world financial analysis and forensics on standard company listings to identify structural fragility, earnings manipulation, and capital allocation quality.

## Objectives
- **Standardized Calculations**: Execute clean, standardized formulas for financial risk profiles (e.g., Beneish M-Score, Piotroski F-Score, Sloan Ratio, ROIC, and Altman Z-Score).
- **Fixed Universe**: Maintain a hardcoded, structured list of companies mapped to specific sectors and sub-sectors to minimize processing overhead and align data inputs.
- **Signal Generation**: Output high-precision metrics that feed into the predictive models and decision matrices.

## Current Setup
1. **Ticker Mapping**: Sector-wise and sub-sector-wise ticker list (to be hardcoded next).
2. **Data Sourcing**: Financial statements (Income Statement, Balance Sheet, Cash Flow) matching the target company universe.
