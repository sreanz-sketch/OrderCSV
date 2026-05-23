# Order CSV Creator — Lessons Learned

Captured during development and debugging sessions, May 2026.

---

## Unleashed API — Serial Numbers

This was the hardest part to get right. Several things tripped us up:

**Serial numbers are NOT on sales order lines.** The `SalesOrderLines[]` in the SalesOrders API response always returns `SerialNumbers: null`, even for serial-tracked products. Serials are only available on shipments — a separate API call is required.

**The correct endpoint is `SalesShipments`, not `Shipments`.** There is no `/Shipments` endpoint. Using the wrong name returns no results silently.

**You must pass `serialBatch=true`.** Without this query parameter, the `SerialNumbers` field on every shipment line returns `null`. The API does not return serial data by default.

**The lines array is called `SalesShipmentLines`, not `ShipmentLines`.** Using the wrong key means you iterate over nothing.

**The serial number value is in `Identifier`, not `SerialNumber`.** The field is named differently on shipment lines than you'd expect from the sales order structure.

**`.get("SerialNumbers", [])` is not safe enough.** When the key exists but the value is `None`, Python's `.get()` returns `None` rather than the default `[]`. This causes a `TypeError: 'NoneType' object is not iterable`. Always use `(value or [])` pattern: `for sn in (line.get("SerialNumbers") or [])`.

---

## CSV Format — Serial-Tracked Products

Non-serial products use a 12-column SOL row. Serial-tracked products need a different structure:

- One SOL row **per serial number** (not one row per order line)
- Quantity is `1` on each row
- Serial number goes in **column 22** (not 23 — easy to get wrong if counting differs)
- Columns 13–21 are empty padding

---

## Streamlit CSS

Streamlit's `st.metric()` component ignores most CSS overrides applied via `st.markdown()`. If you need precise control over font size in metric-style displays, replace `st.metric()` with custom HTML using `st.markdown(..., unsafe_allow_html=True)`. This gives full control over sizing, wrapping, and layout.

---

## Python / General

**`hmac.new` not `hmac.new`** — the Unleashed API uses HMAC-SHA256 signing. The Python `hmac` module function is `hmac.new()`. Easy to confuse with `hashlib`.

**Session state and stale results** — Streamlit stores the last generated result in `st.session_state` so it persists across rerenders. When debugging, always click "Generate CSV" fresh rather than relying on a cached display — the debug panel and the CSV rows come from different points in the render cycle and can show inconsistent state if not refreshed together.
