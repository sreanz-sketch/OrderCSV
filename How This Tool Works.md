# Order CSV Creator — How It Works

## Overview

The Order CSV Creator is a web app (built with Streamlit) that generates warehouse suspended-order CSV files directly from Unleashed Software. You type in a sales order number, click Generate, and the CSV is saved automatically to the right folder — ready for the warehouse or to send to Pacificomm/NZD.

**Launch the app:** double-click `Launch Order CSV App.bat`

---

## What It Does, Step by Step

### 1. You enter an order number
Type any of these formats — they all work:
- `2325`
- `SO-2325`
- `SO-00002325`

### 2. The app fetches the order from Unleashed
It calls the Unleashed API using your API credentials (already saved in the app). It pulls the order header (customer, delivery address, reference) and all order lines (product codes, quantities).

### 3. The app fetches serial numbers from shipments
For any order line with a serial-tracked product (like TWC-V radios), the app makes a second call to Unleashed to get the shipments for that order. Serial numbers are stored on shipments in Unleashed, not on the order itself.

### 4. It builds the CSV
The CSV has no header row. It contains:
- **One SOH row** — the order header (customer, delivery address, etc.)
- **One SOL row per product line** — for standard products
- **One SOL row per serial number** — for serial-tracked products, with the serial number in column 22

### 5. It saves the file automatically
The CSV is saved to:
```
OneDrive > Marathon Products Limited > Warehouse > Orders suspended > SO-XXXXXXXX.csv
```

### 6. You see the results on screen
The app shows:
- Order number, customer name, number of lines, total quantity
- A table of all order lines with product code, description, qty, and serial numbers (if any)
- Delivery address and instructions
- A green confirmation banner

---

## The Buttons

**Download CSV** — downloads the file to your computer (useful if you need to email it or check it).

**Send to Pacificomm** — copies the CSV to the NZD/Pacificomm folder:
```
OneDrive > Marathon Products Limited > Sales orders for NZD > SO-XXXXXXXX.csv
```
Click this when the order is approved for sending to the warehouse.

**View raw CSV file contents** — expandable section showing the exact CSV content that was saved. Useful for checking the format if something looks wrong.

---

## Recent Orders (Sidebar)

The left sidebar shows the last 10 orders you've generated. Each entry shows the SO number, customer name, date, and line count. You can re-download any of them from here if the file still exists on disk.

---

## File Locations

| Purpose | Path |
|---------|------|
| App files | `C:\Users\srean\Documents\CSV creator tool\` |
| Saved CSVs | `OneDrive\...\Warehouse\Orders suspended\` |
| Pacificomm CSVs | `OneDrive\...\Sales orders for NZD\` |
| Order history | `CSV creator tool\recent_orders.json` |

---

## If Something Goes Wrong

**"Order not found"** — double-check the SO number in Unleashed. The order must exist.

**"Could not connect to Unleashed"** — check your internet connection. The app calls the Unleashed API directly.

**"Could not send to Pacificomm"** — make sure OneDrive is synced and the Sales orders for NZD folder exists.

**Serial numbers not showing** — serial numbers only appear if they've been assigned to a shipment in Unleashed. If the order hasn't been shipped/dispatched yet in Unleashed, serials won't be available.

---

## Technical Notes (for troubleshooting or future changes)

- The app is written in Python using the Streamlit framework
- API credentials are hardcoded in `order_csv_app.py` (lines 29–31)
- Serial numbers come from the `SalesShipments` Unleashed endpoint with `serialBatch=true`
- The app must be running (via the .bat launcher) to use it — it's not a background service
- Changing the save folder paths requires editing `order_csv_app.py` (lines 34–35)
