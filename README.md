---
title: Internet Travels Voucher Generator
emoji: 🧾
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: 1.41.1
app_file: app.py
pinned: false
---

# Internet Travels — Voucher Generator

Online hotel/travel voucher generator for Internet Travels (Pvt) Ltd.

- Locked agency identity (name, address, phone, fax, email, licence)
- Dynamic passengers / flights / hotels (add & remove rows)
- One-click PDF voucher in the official Internet Travels layout
- Scannable QR that opens a read-only voucher view when scanned

## Notes

- The QR encodes a link to this app (`/?v=<token>`). The app reads its public
  address automatically from the `SPACE_HOST` environment variable on Hugging
  Face. If the QR ever points at the wrong address, set the **Public app URL**
  field at the top of the app, or add a `BASE_URL` secret in Space settings.
