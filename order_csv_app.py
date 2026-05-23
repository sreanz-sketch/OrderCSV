import streamlit as st
import csv
import os
import io
import json
import requests
import hashlib
import hmac
import base64
import pandas as pd
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Order CSV Creator", page_icon="pkg", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.5rem;padding-bottom:2rem;}
.status-success{background:#e8f5e9;border-left:4px solid #4caf50;border-radius:0 6px 6px 0;padding:.75rem 1rem;color:#1b5e20;font-size:.9rem;}
.status-error{background:#fdecea;border-left:4px solid #f44336;border-radius:0 6px 6px 0;padding:.75rem 1rem;color:#b71c1c;font-size:.9rem;}
div[data-testid="metric-container"]{background:#f8f9fa;border-radius:8px;padding:.6rem .8rem;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1rem !important;}
div[data-testid="metric-container"] [data-testid="stMetricLabel"]{font-size:.75rem !important;}
.sidebar-order{background:#f8f9fa;border-radius:8px;padding:.6rem .8rem;margin-bottom:.5rem;border-left:3px solid #1a4fad;}
.sidebar-so{font-weight:600;font-size:.85rem;color:#111;}
.sidebar-meta{font-size:.75rem;color:#666;margin-top:2px;}
</style>
""", unsafe_allow_html=True)

API_BASE     = "https://api.unleashedsoftware.com"
API_ID       = "4ad4fb7c-a30a-443e-9299-d338c84c6b2c"
API_KEY      = "cpgb7TllT7EWD36AlUrTOQXUBdnzs6GYdpKQW7qwOfT3j0nDPwhDcq94GaDWj4odtzpoTEr8tgm0ixqvmw=="
CLIENT_TYPE  = "marathonproductslimited/api"
SAVE_FOLDER       = r"C:\Users\srean\OneDrive - Marathon Products\Marathon Products Limited\Warehouse\Orders suspended"
PACIFICOMM_FOLDER = r"C:\Users\srean\OneDrive - Marathon Products\Marathon Products Limited\Sales orders for NZD"
SCRIPT_DIR   = Path(__file__).parent
HISTORY_FILE = SCRIPT_DIR / "recent_orders.json"
LOGO_PATH    = SCRIPT_DIR / "logo.png"


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_to_history(entry):
    history = load_history()
    history = [h for h in history if h["so_number"] != entry["so_number"]]
    history.insert(0, entry)
    HISTORY_FILE.write_text(json.dumps(history[:10], indent=2), encoding="utf-8")


def unleashed_get(endpoint, params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    sig = base64.b64encode(
        hmac.new(API_KEY.encode(), query.encode(), hashlib.sha256).digest()
    ).decode()
    url = f"{API_BASE}/{endpoint}?{query}"
    headers = {
        "Accept": "application/json",
        "api-auth-id": API_ID,
        "api-auth-signature": sig,
        "client-type": CLIENT_TYPE,
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def get_serials_from_shipments(order_number):
    """Return {ProductCode: [serial, ...]} from all shipments for this order."""
    try:
        data = unleashed_get("SalesShipments", {
            "orderNumber": order_number,
            "serialBatch": "true",
            "pageSize": "200",
        })
    except Exception as e:
        st.session_state["shipment_debug"] = {"error": str(e)}
        return {}
    st.session_state["shipment_debug"] = data
    serials_by_product = {}
    for shipment in data.get("Items", []):
        for line in (shipment.get("SalesShipmentLines") or []):
            product_code = line.get("Product", {}).get("ProductCode", "")
            line_serials = [
                sn.get("Identifier", "")
                for sn in (line.get("SerialNumbers") or [])
                if sn.get("Identifier")
            ]
            if line_serials:
                serials_by_product.setdefault(product_code, []).extend(line_serials)
    return serials_by_product


def build_csv_rows(order, serials_by_product=None):
    if serials_by_product is None:
        serials_by_product = {}
    customer = order.get("Customer", {})
    rows = [[
        "SOH", order["OrderNumber"], "",
        customer.get("CustomerCode", ""),
        order.get("CustomerRef", ""), "",
        order.get("DeliveryName", ""),
        order.get("DeliveryStreetAddress", ""),
        order.get("DeliveryStreetAddress2", ""),
        order.get("DeliveryCity", ""), "",
        order.get("DeliveryInstruction", ""),
    ]]
    for line in order.get("SalesOrderLines", []):
        product_code = line["Product"]["ProductCode"]
        serial_numbers = serials_by_product.get(product_code, [])
        if serial_numbers:
            # One SOL row per serial number; serial number goes in column 23 (index 22)
            for serial in serial_numbers:
                sol_row = [
                    "SOL",                             # col 1
                    order["OrderNumber"],              # col 2
                    "",                                # col 3
                    customer.get("CustomerCode", ""),  # col 4
                    order.get("CustomerRef", ""),      # col 5
                    product_code,                      # col 6
                    "",                                # col 7
                    "",                                # col 8
                    "",                                # col 9
                    1,                                 # col 10
                    "",                                # col 11
                    "",                                # col 12
                    "",                                # col 13
                    "",                                # col 14
                    "",                                # col 15
                    "",                                # col 16
                    "",                                # col 17
                    "",                                # col 18
                    "",                                # col 19
                    "",                                # col 20
                    "",                                # col 21
                    serial,                            # col 22
                ]
                rows.append(sol_row)
        else:
            rows.append([
                "SOL", order["OrderNumber"], "",
                customer.get("CustomerCode", ""),
                order.get("CustomerRef", ""),
                product_code,
                "", "", "",
                line["OrderQuantity"], "", "",
            ])
    return rows


def rows_to_csv_bytes(rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def normalise_so(raw):
    raw = raw.strip()
    digits = raw[3:].lstrip("0") if raw.upper().startswith("SO-") else raw.lstrip("0")
    return f"SO-{digits.zfill(8)}"


def show_result(so_number, customer_name, customer_ref, total_qty, lines, order, rows, serials_by_product=None):
    if serials_by_product is None:
        serials_by_product = {}
    def metric_html(label, value):
        return (
            f"<div style='background:#f8f9fa;border-radius:8px;padding:.6rem .8rem;'>"
            f"<div style='font-size:.75rem;color:#666;margin-bottom:2px;'>{label}</div>"
            f"<div style='font-size:1rem;font-weight:600;color:#111;word-break:break-word;'>{value}</div>"
            f"</div>"
        )
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(metric_html("Order",     so_number),     unsafe_allow_html=True)
    m2.markdown(metric_html("Customer",  customer_name), unsafe_allow_html=True)
    m3.markdown(metric_html("Lines",     len(lines)),    unsafe_allow_html=True)
    m4.markdown(metric_html("Total qty", total_qty),     unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([2, 1])

    with left:
        st.markdown("**Order lines**")
        table_data = []
        for line in lines:
            product = line.get("Product", {})
            product_code = product.get("ProductCode", "")
            serials = serials_by_product.get(product_code, [])
            table_data.append({
                "Product code":   product_code,
                "Description":    product.get("ProductDescription", ""),
                "Qty":            int(line.get("OrderQuantity", 0)),
                "Serial numbers": ", ".join(serials) if serials else "—",
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    with right:
        st.markdown("**Delivery details**")
        addr_parts = [
            order.get("DeliveryName", ""),
            order.get("DeliveryStreetAddress", ""),
            order.get("DeliveryStreetAddress2", ""),
            order.get("DeliveryCity", ""),
        ]
        detail = "\n".join(p for p in addr_parts if p) or "---"
        instruction = order.get("DeliveryInstruction", "")
        if instruction:
            detail += f"\n\nInstructions: {instruction}"
        detail += f"\n\nRef: {customer_ref}"
        st.text(detail)

    st.write("")

    with st.expander("View raw CSV file contents"):
        st.code("\n".join(",".join(str(c) for c in row) for row in rows), language=None)

    st.write("")

    st.markdown(
        f'<div class="status-success">Saved: {so_number}.csv to Warehouse\\Orders suspended</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    dl_col, pac_col, _ = st.columns([1, 1, 2])
    with dl_col:
        st.download_button(
            label="Download CSV",
            data=rows_to_csv_bytes(rows),
            file_name=f"{so_number}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with pac_col:
        if st.button("Send to Pacificomm", use_container_width=True):
            try:
                os.makedirs(PACIFICOMM_FOLDER, exist_ok=True)
                src = os.path.join(SAVE_FOLDER, f"{so_number}.csv")
                dst = os.path.join(PACIFICOMM_FOLDER, f"{so_number}.csv")
                import shutil
                shutil.copy2(src, dst)
                st.markdown(
                    f'<div class="status-success">Sent to Pacificomm: {so_number}.csv</div>',
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.markdown(
                    f'<div class="status-error">Could not send to Pacificomm: {e}</div>',
                    unsafe_allow_html=True,
                )


# Sidebar
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.markdown(
            "<div style='font-size:1.1rem;font-weight:700;color:#1a4fad;padding:.5rem 0 1rem;'>Marathon Products</div>",
            unsafe_allow_html=True,
        )
    st.markdown("### Recent orders")
    history = load_history()
    if not history:
        st.caption("No orders generated yet.")
    else:
        for entry in history:
            csv_path = entry.get("csv_path", "")
            st.markdown(
                "<div class='sidebar-order'>"
                f"<div class='sidebar-so'>{entry['so_number']}</div>"
                f"<div class='sidebar-meta'>{entry.get('customer', '---')}</div>"
                f"<div class='sidebar-meta'>{entry.get('date', '')} | {entry.get('line_count', 0)} lines</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if os.path.exists(csv_path):
                with open(csv_path, "rb") as fh:
                    st.download_button(
                        label="Re-download",
                        data=fh.read(),
                        file_name=f"{entry['so_number']}.csv",
                        mime="text/csv",
                        key=f"dl_{entry['so_number']}",
                        use_container_width=True,
                    )
            else:
                st.caption("File no longer on disk")

# Main
st.title("Order CSV Creator")
st.caption("Generates a suspended-order CSV and saves it to Warehouse > Orders suspended")
st.divider()

col1, col2, _ = st.columns([1.5, 1.2, 5])
with col1:
    raw_input = st.text_input(
        "Sales order number",
        placeholder="e.g. 2321",
        help="Enter just the digits or the full SO-XXXXXXXX -- both work.",
    )
with col2:
    st.write("")
    st.write("")
    generate = st.button("Generate CSV", type="primary", use_container_width=True)

if generate:
    if not raw_input.strip():
        st.markdown('<div class="status-error">Please enter a sales order number.</div>', unsafe_allow_html=True)
        st.stop()

    so_number = normalise_so(raw_input)

    with st.spinner(f"Fetching {so_number} from Unleashed..."):
        try:
            data = unleashed_get("SalesOrders", {"pageSize": "1", "orderNumber": so_number})
        except requests.HTTPError as e:
            st.markdown(f'<div class="status-error">Unleashed API error: {e}</div>', unsafe_allow_html=True)
            st.stop()
        except Exception as e:
            st.markdown(f'<div class="status-error">Could not connect to Unleashed: {e}</div>', unsafe_allow_html=True)
            st.stop()

    with st.spinner(f"Fetching shipments for {so_number}..."):
        serials_by_product = get_serials_from_shipments(so_number)

    items = data.get("Items", [])
    if not items:
        st.markdown(
            f'<div class="status-error">Order {so_number} not found. Check the number and try again.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    order         = items[0]
    lines         = order.get("SalesOrderLines", [])
    customer      = order.get("Customer", {})
    rows          = build_csv_rows(order, serials_by_product)
    customer_name = customer.get("CustomerName", "---")
    customer_ref  = order.get("CustomerRef", "---") or "---"
    total_qty     = int(sum(l.get("OrderQuantity", 0) for l in lines))

    os.makedirs(SAVE_FOLDER, exist_ok=True)
    csv_path = os.path.join(SAVE_FOLDER, f"{so_number}.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)

    save_to_history({
        "so_number":  so_number,
        "customer":   customer_name,
        "date":       datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "line_count": len(lines),
        "total_qty":  total_qty,
        "csv_path":   csv_path,
    })

    # Store in session state for persistence, then display immediately
    st.session_state["result"] = dict(
        so_number=so_number, customer_name=customer_name,
        customer_ref=customer_ref, total_qty=total_qty,
        lines=lines, order=order, rows=rows, serials_by_product=serials_by_product,
    )
    show_result(so_number, customer_name, customer_ref, total_qty, lines, order, rows, serials_by_product)

elif "result" in st.session_state:
    res = st.session_state["result"]
    show_result(
        res["so_number"], res["customer_name"], res["customer_ref"],
        res["total_qty"], res["lines"], res["order"], res["rows"],
        res.get("serials_by_product", {}),
    )

st.divider()
st.caption(f"Saves to: {SAVE_FOLDER}")

