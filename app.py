"""
Internet Travels — Hotel / Travel Voucher Generator
---------------------------------------------------
Streamlit app (CPU-only, Hugging Face ready).

Key design points:
- Agency identity fields are LOCKED constants (not editable).
- Passengers / Flights / Hotels are DYNAMIC tables (add & remove rows).
- One clean PDF in the official Internet Travels layout.
- Self-contained QR (top-right of header) carrying ALL voucher data as
  compact JSON, using ERROR_CORRECT_M so it stays scannable when printed.

PDF / QR builders are pure functions (no Streamlit calls) so they can be
unit-tested headless. The Streamlit UI lives in main().
"""

import json
import os
import zlib
from io import BytesIO

import qrcode
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --------------------------------------------------------------------------- #
# LOCKED AGENCY CONSTANTS  (single source of truth — never user-editable)      #
# --------------------------------------------------------------------------- #
AGENCY = {
    "name":        "INTERNET TRAVELS (PRIVATE) LIMITED",
    "footer_name": "INTERNET TRAVELS (PVT) LTD.",
    "address":     "B-5/6 Mehran VIP Complex, Dr. Dawood Pota Road, "
                   "Near Cantt Station, Karachi",
    "phone":       "021-35212181, 35212198",
    "fax":         "0213-5689717",
    "email":       "internettravels_786@yahoo.com",
    "licence":     "1836",
}

import base64
# Internet Travels logo (extracted from their Word voucher), embedded so the
# app stays a single self-contained file.
LOGO_B64 = (
    "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"
)


def _logo_buf():
    return BytesIO(base64.b64decode(LOGO_B64))


BRAND = colors.HexColor("#1e3a5f")
HEAD_BG = colors.HexColor("#d9d9d9")
LIGHT_BG = colors.HexColor("#f5f5f5")

# Canonical columns — single source of truth for tables, QR and PDF.
PAX_FIELDS = ["Pax Name", "Passport No", "Type"]
FLT_FIELDS = ["Action", "Airline", "Flight No", "Sector", "Date", "ETD", "ETA", "PNR"]
HTL_FIELDS = ["City", "Hotel Name", "Room Type", "Check In", "Check Out", "Nights", "Status"]


# --------------------------------------------------------------------------- #
# Sanitizers — make ANY edited data safe (no NaN/None ever reaches QR or PDF)  #
# --------------------------------------------------------------------------- #
def _s(x):
    """Coerce anything (None, NaN, float, int, str) into a clean string."""
    if x is None:
        return ""
    if isinstance(x, float):
        if x != x:            # NaN
            return ""
        if x.is_integer():    # 3.0 -> "3"
            return str(int(x))
        return str(x)
    return str(x).strip()


def clean_records(rows, fields):
    """Return list of dicts with exactly `fields`, sanitized, blank rows dropped."""
    out = []
    for r in (rows or []):
        if not isinstance(r, dict):
            continue
        rec = {f: _s(r.get(f, "")) for f in fields}
        if any(rec[f] for f in fields):
            out.append(rec)
    return out


def clean_book(book):
    return {k: _s(v) for k, v in (book or {}).items()}


def norm_url(u):
    """Normalize the public app URL; prepend https:// if scheme missing."""
    u = _s(u).rstrip("/")
    if u and not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def safe_filename(s, fallback="IT"):
    keep = "".join(c if (c.isalnum() or c in "-_") else "_" for c in _s(s))
    keep = keep.strip("_")
    return keep or fallback


# --------------------------------------------------------------------------- #
# QR                                                                          #
# --------------------------------------------------------------------------- #
def qr_payload(book, pax, flights, hotels):
    """Compact JSON of the whole voucher. Inputs are sanitized defensively."""
    book = clean_book(book)
    pax = clean_records(pax, PAX_FIELDS)
    flights = clean_records(flights, FLT_FIELDS)
    hotels = clean_records(hotels, HTL_FIELDS)
    payload = {
        "agency": "Internet Travels (Pvt) Ltd",
        "lic": AGENCY["licence"],
        "ref": book.get("our_ref", ""),
        "yref": book.get("your_ref", ""),
        "pkg": book.get("package_title", ""),
        "care": book.get("care_of", ""),
        "issue": book.get("issue_date", ""),
        "pax": [[p[f] for f in PAX_FIELDS] for p in pax],
        "flt": [[f[k] for k in FLT_FIELDS] for f in flights],
        "htl": [[h[k] for k in HTL_FIELDS] for h in hotels],
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def build_qr(text):
    """Return (PNG BytesIO, version). Tries ECC_M then ECC_L if data is large,
    so a big voucher degrades gracefully instead of crashing."""
    text = text if (text and str(text).strip()) else " "
    last_err = None
    for ecc in (qrcode.constants.ERROR_CORRECT_M, qrcode.constants.ERROR_CORRECT_L):
        try:
            qr = qrcode.QRCode(version=None, error_correction=ecc,
                               box_size=10, border=4)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf, qr.version
        except qrcode.exceptions.DataOverflowError as e:
            last_err = e
            continue
    raise ValueError("Too much data for one QR code — reduce rows.") from last_err


# --------------------------------------------------------------------------- #
# Voucher <-> URL token  (lets the QR encode a link that OPENS the voucher)    #
# --------------------------------------------------------------------------- #
def encode_token(book, pax, flights, hotels):
    """Compress the voucher JSON into a short URL-safe token."""
    raw = qr_payload(book, pax, flights, hotels).encode("utf-8")
    comp = zlib.compress(raw, 9)
    return base64.urlsafe_b64encode(comp).decode("ascii")


def decode_token(token):
    comp = base64.urlsafe_b64decode(token.encode("ascii"))
    return json.loads(zlib.decompress(comp).decode("utf-8"))


def detect_base_url():
    """Public URL of this app, in priority order:
    1) APP_URL constant below (set this after deploying)
    2) BASE_URL environment variable
    3) Streamlit secret  BASE_URL
    4) SPACE_HOST  (auto-set on Hugging Face)
    """
    # 1) Hardcode your live app address here after you deploy, e.g.
    #    APP_URL = "https://internet-travels-voucher.streamlit.app"
    APP_URL = ""
    if APP_URL:
        return APP_URL.rstrip("/")
    if os.environ.get("BASE_URL"):
        return os.environ["BASE_URL"].rstrip("/")
    try:
        import streamlit as st
        if "BASE_URL" in st.secrets:
            return str(st.secrets["BASE_URL"]).rstrip("/")
    except Exception:
        pass
    if os.environ.get("SPACE_HOST"):
        return "https://" + os.environ["SPACE_HOST"].rstrip("/")
    return ""  # unknown -> user types it into the field


# --------------------------------------------------------------------------- #
# PDF                                                                         #
# --------------------------------------------------------------------------- #
def _clean(rows, key_fields):
    """Drop rows where all key fields are blank."""
    out = []
    for r in rows:
        if any(str(r.get(k, "")).strip() for k in key_fields):
            out.append(r)
    return out


def _esc(x):
    """Escape text for reportlab Paragraph mini-HTML so &, <, > never break it."""
    return (_s(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def qr_print_cm(version):
    """Scale printed QR to payload so module size stays ~>=0.4mm (scannable)."""
    if not version or version <= 13:
        return 3.0
    if version <= 17:
        return 3.5
    return 4.0


def build_pdf(book, sponsor, pax, flights, hotels, qr_png, qr_version=None):
    book = clean_book(book)
    sponsor = clean_book(sponsor)
    pax = clean_records(pax, PAX_FIELDS)
    flights = clean_records(flights, FLT_FIELDS)
    hotels = clean_records(hotels, HTL_FIELDS)
    if isinstance(qr_png, BytesIO):
        qr_png = qr_png.getvalue()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1.0 * cm, bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    s_small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, leading=11)
    s_bold = ParagraphStyle("bold", parent=s_small, fontName="Helvetica-Bold")
    s_lbl = ParagraphStyle("lbl", parent=s_small, fontName="Helvetica-Bold", textColor=BRAND)
    s_sec = ParagraphStyle("sec", parent=styles["Heading2"], fontSize=11,
                           textColor=BRAND, spaceBefore=4, spaceAfter=4)

    story = []

    # ---- Header: agency (left) + QR (right) ---------------------------------
    agency_block = Paragraph(
        f"<b><font size=13 color='#1e3a5f'>{AGENCY['name']}</font></b><br/>"
        f"<font size=8>{AGENCY['address']}</font><br/>"
        f"<font size=8>Phone: {AGENCY['phone']} &nbsp;|&nbsp; Fax: {AGENCY['fax']}</font><br/>"
        f"<font size=8>Email: {AGENCY['email']}</font><br/>"
        f"<font size=8><b>Govt. Licence No. {AGENCY['licence']}</b></font>",
        s_small,
    )
    qcm = qr_print_cm(qr_version)
    qr_img = Image(BytesIO(qr_png), width=qcm * cm, height=qcm * cm)
    right_w = (qcm + 0.3) * cm
    try:
        logo_flow = Image(_logo_buf(), width=1.5 * cm, height=1.5 * cm * 48 / 56)
    except Exception:
        logo_flow = Spacer(1.5 * cm, 1.5 * cm)
    left = Table([[logo_flow, agency_block]], colWidths=[1.7 * cm, None])
    left.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
    ]))
    header = Table([[left, qr_img]],
                   colWidths=[16.6 * cm - right_w, right_w])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>HOTEL VOUCHER</b>", ParagraphStyle(
        "hv", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER,
        textColor=BRAND, spaceAfter=6)))

    # ---- Booking + Sponsor block --------------------------------------------
    def pr(label, val):
        return Paragraph(f"<b>{label}</b>", s_lbl), Paragraph(_esc(val), s_small)

    booking_rows = [
        [*pr("Our Ref. No.", book.get("our_ref")), *pr("Your Ref. No.", book.get("your_ref"))],
        [*pr("Booking Date", book.get("booking_date")), *pr("Issue Date", book.get("issue_date"))],
        [*pr("Package Title", book.get("package_title")), *pr("Care Of", book.get("care_of"))],
    ]
    booking_tbl = Table(booking_rows, colWidths=[3.0 * cm, 5.3 * cm, 3.0 * cm, 5.3 * cm])
    booking_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(booking_tbl)

    if any(sponsor.get(k, "") for k in sponsor):
        story.append(Spacer(1, 4))
        sp = Paragraph(
            f"<b>Sponsor:</b> {_esc(sponsor.get('sponsor'))} &nbsp; "
            f"<b>Address:</b> {_esc(sponsor.get('address'))} &nbsp; "
            f"<b>City:</b> {_esc(sponsor.get('city'))} &nbsp; "
            f"<b>Tel:</b> {_esc(sponsor.get('tel'))} &nbsp; "
            f"<b>Fax:</b> {_esc(sponsor.get('fax'))}", s_small)
        story.append(sp)
    story.append(Spacer(1, 10))

    # ---- Passengers ---------------------------------------------------------
    story.append(Paragraph("Issued To", s_sec))
    pax_head = [Paragraph("<b>S.#</b>", s_bold), Paragraph("<b>Pax Name</b>", s_bold),
                Paragraph("<b>Passport No</b>", s_bold), Paragraph("<b>Type</b>", s_bold)]
    pax_data = [pax_head]
    for i, p in enumerate(pax, 1):
        pax_data.append([
            Paragraph(str(i), s_small),
            Paragraph(_esc(p.get("Pax Name")), s_small),
            Paragraph(_esc(p.get("Passport No")), s_small),
            Paragraph(_esc(p.get("Type")), s_small),
        ])
    if len(pax_data) == 1:
        pax_data.append([Paragraph("", s_small) for _ in range(4)])
    pax_tbl = Table(pax_data, colWidths=[1.2 * cm, 8.6 * cm, 4.4 * cm, 2.4 * cm])
    pax_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(pax_tbl)
    story.append(Spacer(1, 10))

    # ---- Flights ------------------------------------------------------------
    story.append(Paragraph("Arrival / Departure Details", s_sec))
    flt_cols = ["Action", "Airline", "Flight No", "Sector", "Date", "ETD", "ETA", "PNR"]
    flt_data = [[Paragraph(f"<b>{c}</b>", s_bold) for c in flt_cols]]
    for f in flights:
        flt_data.append([Paragraph(_esc(f.get(c)), s_small) for c in flt_cols])
    if len(flt_data) == 1:
        flt_data.append([Paragraph("", s_small) for _ in flt_cols])
    flt_tbl = Table(flt_data, colWidths=[2.4 * cm, 1.9 * cm, 1.9 * cm, 2.6 * cm,
                                         2.4 * cm, 1.7 * cm, 1.7 * cm, 2.0 * cm])
    flt_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(flt_tbl)
    story.append(Spacer(1, 10))

    # ---- Service / Hotel details -------------------------------------------
    story.append(Paragraph("Service Details", s_sec))
    svc_data = [[Paragraph("<b>Type</b>", s_bold), Paragraph("<b>Date &amp; Time</b>", s_bold),
                 Paragraph("<b>Description</b>", s_bold), Paragraph("<b>Ref. No.</b>", s_bold),
                 Paragraph("<b>Status</b>", s_bold)]]
    for h in hotels:
        desc = (f"<b>{_esc(h.get('Hotel Name'))}</b>, {_esc(h.get('City'))}<br/>"
                f"{_esc(h.get('Room Type'))}<br/>"
                f"For {_esc(h.get('Nights'))} Nights from {_esc(h.get('Check In'))} "
                f"To {_esc(h.get('Check Out'))}")
        svc_data.append([
            Paragraph("Hotel", s_small),
            Paragraph(f"{_esc(h.get('Check In'))} 16:00", s_small),
            Paragraph(desc, s_small),
            Paragraph(_esc(book.get("our_ref")), s_small),
            Paragraph(_esc(h.get("Status")), s_small),
        ])
    if len(svc_data) == 1:
        svc_data.append([Paragraph("", s_small) for _ in range(5)])
    svc_tbl = Table(svc_data, colWidths=[1.8 * cm, 3.0 * cm, 7.0 * cm, 2.4 * cm, 2.4 * cm])
    svc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(svc_tbl)
    story.append(Spacer(1, 24))

    # ---- Footer -------------------------------------------------------------
    footer = Table([[
        Paragraph(f"Prepared by: {_esc(book.get('prepared_by'))}", s_small),
        Paragraph(f"Checked by: {_esc(book.get('checked_by'))}", s_small),
        Paragraph(f"<b>For {AGENCY['footer_name']}</b><br/><br/>"
                  f"Signature &amp; Stamp", s_small),
    ]], colWidths=[5.5 * cm, 5.5 * cm, 5.6 * cm])
    footer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(footer)

    doc.build(story)
    buffer.seek(0)
    return buffer


# --------------------------------------------------------------------------- #
# STREAMLIT UI                                                                #
# --------------------------------------------------------------------------- #
def render_viewer(st, token):
    """Read-only voucher shown when someone scans the QR / opens the link."""
    try:
        v = decode_token(token)
        if not isinstance(v, dict):
            raise ValueError
    except Exception:
        st.error("This voucher link is invalid or corrupted.")
        return
    try:
        st.image(_logo_buf(), width=80)
    except Exception:
        pass
    st.markdown(f"### {AGENCY['name']}")
    st.caption(f"{AGENCY['address']} · Licence {AGENCY['licence']}")
    st.markdown("## 🧾 Hotel Voucher")
    c1, c2, c3 = st.columns(3)
    c1.metric("Our Ref.", v.get("ref") or "—")
    c2.metric("Package", v.get("pkg") or "—")
    c3.metric("Care Of", v.get("care") or "—")

    def _table(title, rows, cols):
        rows = [r for r in (rows or []) if isinstance(r, (list, tuple))]
        norm = [(list(r) + [""] * len(cols))[:len(cols)] for r in rows]
        if norm:
            st.markdown(f"#### {title}")
            st.table(pd.DataFrame(norm, columns=cols))

    _table("Passengers", v.get("pax"), ["Name", "Passport", "Type"])
    _table("Flights", v.get("flt"),
           ["Action", "Airline", "Flight", "Sector", "Date", "ETD", "ETA", "PNR"])
    _table("Hotels", v.get("htl"),
           ["City", "Hotel", "Room Type", "Check In", "Check Out", "Nights", "Status"])
    st.caption(f"Verified voucher · For {AGENCY['footer_name']}")


def main():
    import streamlit as st

    st.set_page_config(page_title="Internet Travels — Voucher Generator",
                       page_icon="🧾", layout="wide")

    # Viewer mode: opened from a scanned QR (…/?v=<token>)
    token = st.query_params.get("v")
    if token:
        render_viewer(st, token)
        return

    st.title("🧾 Internet Travels — Voucher Generator")
    st.caption("Locked agency identity · dynamic pax/flights/hotels · scannable QR")

    base_url = st.text_input(
        "Public app URL (used in the QR link)",
        detect_base_url(),
        help="On Hugging Face this auto-fills from SPACE_HOST. The QR opens "
             "this URL, so it must be the live address of this Space.",
    )

    # ---- Locked agency identity (display only) ------------------------------
    with st.container(border=True):
        lg, hd = st.columns([1, 6])
        lg.image(_logo_buf(), width=64)
        hd.markdown("#### 🏢 Agency (locked)")
        c1, c2 = st.columns(2)
        c1.text_input("Agency Name", AGENCY["name"], disabled=True)
        c1.text_input("Phone", AGENCY["phone"], disabled=True)
        c1.text_input("Email", AGENCY["email"], disabled=True)
        c2.text_input("Address", AGENCY["address"], disabled=True)
        c2.text_input("Fax", AGENCY["fax"], disabled=True)
        c2.text_input("Govt. Licence No.", AGENCY["licence"], disabled=True)

    # ---- Booking + sponsor --------------------------------------------------
    st.markdown("#### 📅 Booking Info")
    b1, b2, b3 = st.columns(3)
    book = {
        "our_ref":     b1.text_input("Our Ref. No.", "UB015412"),
        "your_ref":    b1.text_input("Your Ref. No.", ""),
        "booking_date": b2.text_input("Booking Date", "04-Jul-25"),
        "issue_date":  b2.text_input("Issue Date", "04-Jul-25"),
        "package_title": b3.text_input("Package Title", "Madinah Hotel"),
        "care_of":     b3.text_input("Care Of", "Mr. Toufique Ahmed Chandio"),
    }

    with st.expander("Sponsor details (optional)"):
        sc1, sc2 = st.columns(2)
        sponsor = {
            "sponsor": sc1.text_input("Sponsor", ""),
            "address": sc1.text_input("Sponsor Address", ""),
            "city":    sc1.text_input("Sponsor City", ""),
            "tel":     sc2.text_input("Sponsor Tel", ""),
            "fax":     sc2.text_input("Sponsor Fax", ""),
        }

    # ---- Dynamic tables -----------------------------------------------------
    st.markdown("#### 👥 Passengers")
    pax_df = st.data_editor(
        pd.DataFrame([{"Pax Name": "Mr. Toufique Ahmed Chandio",
                       "Passport No": "", "Type": "Adult"}]),
        num_rows="dynamic", use_container_width=True, key="pax",
        column_config={"Type": st.column_config.SelectboxColumn(
            options=["Adult", "Child", "Infant"])},
    )

    st.markdown("#### ✈️ Flights")
    flt_df = st.data_editor(
        pd.DataFrame([{"Action": "Departure", "Airline": "", "Flight No": "",
                       "Sector": "", "Date": "08-Jul-25", "ETD": "", "ETA": "", "PNR": ""}]),
        num_rows="dynamic", use_container_width=True, key="flt",
        column_config={"Action": st.column_config.SelectboxColumn(
            options=["Departure", "Arrival"])},
    )

    st.markdown("#### 🏨 Hotels")
    htl_df = st.data_editor(
        pd.DataFrame([{"City": "Madinah", "Hotel Name": "Maden Hotel",
                       "Room Type": "Quad Bed with Buffet Breakfast",
                       "Check In": "08-Jul-25", "Check Out": "11-Jul-25",
                       "Nights": 3, "Status": "Confirm"}]),
        num_rows="dynamic", use_container_width=True, key="htl",
        column_config={"Status": st.column_config.SelectboxColumn(
            options=["Confirm", "Pending", "Cancelled"])},
    )

    st.markdown("#### ✍️ Signatures")
    g1, g2 = st.columns(2)
    book["prepared_by"] = g1.text_input("Prepared by", "")
    book["checked_by"] = g2.text_input("Checked by", "")

    # Sanitize EVERYTHING once, here. From this point on, data is safe.
    book = clean_book(book)
    sponsor = clean_book(sponsor)
    pax = clean_records(pax_df.to_dict("records"), PAX_FIELDS)
    flights = clean_records(flt_df.to_dict("records"), FLT_FIELDS)
    hotels = clean_records(htl_df.to_dict("records"), HTL_FIELDS)
    base_url = norm_url(base_url)
    fname = safe_filename(book.get("our_ref"))

    # ---- QR (encodes a LINK that opens the voucher) -------------------------
    st.markdown("---")
    payload = qr_payload(book, pax, flights, hotels)          # full data (JSON download)
    token = encode_token(book, pax, flights, hotels)          # compressed token
    qr_content = f"{base_url}/?v={token}" if base_url else payload
    try:
        qr_buf, ver = build_qr(qr_content)
        qr_png = qr_buf.getvalue()
    except Exception as e:
        st.error(f"Could not build the QR: {e}  (Try removing a few rows.)")
        return

    qcol1, qcol2 = st.columns([1, 2])
    qcol1.image(qr_png, caption=f"QR (version {ver})", width=220)
    if base_url:
        qcol2.success("✅ QR opens the voucher link when scanned.")
        qcol2.caption(f"Link length: {len(qr_content)} chars")
    else:
        qcol2.warning("⚠️ No app URL set — the QR holds raw data and won't *open* "
                      "anything when scanned. Add the public app URL at the top so "
                      "the QR becomes a clickable link.")
    qcol2.caption(f"{len(pax)} pax · {len(flights)} flight(s) · {len(hotels)} hotel(s)")
    if ver and ver > 22:
        qcol2.warning("QR is very dense — fewer rows will scan more reliably.")

    # ---- Generate PDF -------------------------------------------------------
    if st.button("📄 Generate Voucher PDF", type="primary", use_container_width=True):
        try:
            pdf = build_pdf(book, sponsor, pax, flights, hotels, qr_png, ver)
            st.download_button(
                "⬇️ Download Voucher PDF", data=pdf,
                file_name=f"voucher_{fname}.pdf",
                mime="application/pdf", use_container_width=True,
            )
        except Exception as e:
            st.error(f"Could not build the PDF: {e}")

    st.download_button("⬇️ Download QR (PNG)", data=qr_png,
                       file_name=f"qr_{fname}.png", mime="image/png")
    st.download_button("⬇️ Download Voucher Data (JSON)", data=payload,
                       file_name=f"voucher_{fname}.json",
                       mime="application/json")


if __name__ == "__main__":
    main()
