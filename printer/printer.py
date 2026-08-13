# -*- coding: utf-8 -*-
"""
printer.py
----------
Local print service used by app.py to send receipts to the
WDLink WD8260 thermal printer (80 mm paper) connected in USB.

Design goals:
- Never crash the main app if the printer is missing/misconfigured.
- Use ESC/POS commands via the `python-escpos` library when available.
- If python-escpos or the printer is not available, fall back to
  generating a plain-text ticket (still usable / printable manually,
  and shown to the user in the browser).

See printer/README.md for how to identify and configure your WD8260
USB Vendor ID / Product ID on Windows 10.
"""

import os
import textwrap
from datetime import datetime

# Ticket width in characters for 80mm paper with a standard font (~42-48 chars)
LINE_WIDTH = 42

# ---------------------------------------------------------------------------
# USB IDs for the WDLink WD8260.
# These are placeholders — every USB thermal printer reports a Vendor ID
# (idVendor) and Product ID (idProduct). Update these two values after
# identifying your printer (see printer/README.md, section "Identify the
# printer"). Many WD8260 units are re-badged generic ESC/POS printers that
# use the common 0x0483 (STMicroelectronics) or 0x0416 (WinChipHead) chipsets
# — but this varies per unit, so it MUST be verified on the target PC.
# ---------------------------------------------------------------------------
PRINTER_VENDOR_ID = os.environ.get("WD8260_VENDOR_ID", "0x0483")
PRINTER_PRODUCT_ID = os.environ.get("WD8260_PRODUCT_ID", "0x5743")


class PrinterNotAvailable(Exception):
    """Raised internally when the physical printer can't be reached."""
    pass


def _try_import_escpos():
    try:
        from escpos.printer import Usb  # python-escpos
        return Usb
    except Exception:
        return None


def _try_import_win32print():
    try:
        import win32print
        return win32print
    except Exception:
        return None


def find_windows_printer(preferred=None):
    """
    Returns the name of an installed Windows printer to use for printing.
    Priority:
      1. `preferred` (e.g. the name saved in settings) if it is installed.
      2. Any installed printer whose name contains '8260' or 'wd'.
      3. The default Windows printer.
    Returns None if no usable printer is found.
    """
    win32print = _try_import_win32print()
    if win32print is None:
        return None

    try:
        printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL + win32print.PRINTER_ENUM_CONNECTIONS)]
    except Exception:
        printers = []

    def norm(s):
        return (s or "").lower()

    if preferred:
        for p in printers:
            if norm(p) == norm(preferred):
                return p
        for p in printers:
            if norm(preferred) in norm(p):
                return p

    for p in printers:
        if "8260" in norm(p) or "wd" in norm(p):
            return p

    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        pass

    return printers[0] if printers else None


def print_via_windows(printer_name, text, line_width=LINE_WIDTH):
    """
    Sends the plain-text ticket straight to a Windows-installed printer
    (bypasses the broken pyusb/libusb USB backend). The data is prefixed
    with an ESC/POS reset and suffixed with a paper feed + cut, which any
    native ESC/POS printer handles — including the WD8260.
    Returns True on success, False otherwise.
    """
    win32print = _try_import_win32print()
    if win32print is None or not printer_name:
        return False

    ascii_text = (
        text
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )

    raw = "\x1b@".encode("latin-1")                    # ESC @ : reset printer
    raw += ascii_text.encode("latin-1")
    raw += b"\n\n" + b"\x1b" + b"d" + b"\x03"          # ESC d 3 : feed 3 lines
    raw += b"\x1d\x56\x42\x00"                          # GS V B 0 : full cut

    try:
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hprinter, 1, ("stock_ticket", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, raw)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
        return True
    except Exception:
        return False


def get_printer_status():
    """
    Returns a dict describing whether the printer looks reachable.
    This never raises — it is used by the /settings page and dashboard
    to show 'Printer connected' vs 'Printer not detected'.
    """
    Usb = _try_import_escpos()
    if Usb is not None:
        try:
            vendor_id = int(PRINTER_VENDOR_ID, 16)
            product_id = int(PRINTER_PRODUCT_ID, 16)
            printer = Usb(vendor_id, product_id, timeout=0, in_ep=0x82, out_ep=0x01)
            printer.close()
            return {"available": True, "detail": "Imprimante détectée en USB."}
        except Exception:
            pass  # try the Windows printer route below

    printer_name = find_windows_printer()
    if printer_name:
        return {
            "available": True,
            "detail": f"Imprimante Windows détectée : {printer_name}",
        }

    if Usb is None:
        return {
            "available": False,
            "detail": "Librairie python-escpos non installée. "
                      "Le module d'impression fonctionne en mode ticket texte.",
        }

    return {
        "available": False,
        "detail": "Imprimante non détectée. Configurez-la comme imprimante "
                  "Windows ou vérifiez les identifiants USB "
                  f"({PRINTER_VENDOR_ID}/{PRINTER_PRODUCT_ID}).",
    }


def build_receipt_text(store, sale, items):
    """
    Builds a plain-text version of the receipt, formatted for 80mm paper
    (LINE_WIDTH characters wide). This text is:
      - shown in the browser as a fallback / preview
      - used as the basis for the ESC/POS ticket
      - what gets returned to the frontend for a printable HTML view

    store: dict with store_name, store_address, store_phone
    sale: dict with sale_number, total, created_at
    items: list of dicts with name, quantity, unit_price, subtotal
    """
    lines = []
    center = lambda s: s.center(LINE_WIDTH)

    lines.append(center(store.get("store_name", "STOCK APP")))
    if store.get("store_address"):
        lines.append(center(store["store_address"]))
    if store.get("store_phone"):
        lines.append(center(store["store_phone"]))
    lines.append("-" * LINE_WIDTH)
    lines.append(f"Vente : {sale['sale_number']}")
    created = sale.get("created_at", "")
    try:
        dt = datetime.fromisoformat(created)
        date_str = dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_str = created
    lines.append(f"Date  : {date_str}")
    lines.append("-" * LINE_WIDTH)
    lines.append(f"{'Produit':<20}{'Qte':>5}{'Prix':>8}{'Total':>9}")
    lines.append("-" * LINE_WIDTH)

    for item in items:
        name = item["name"]
        for wrapped in textwrap.wrap(name, 20) or [""]:
            lines.append(wrapped)
        qte = str(item["quantity"])
        prix = f"{item['unit_price']:.2f}"
        total = f"{item['subtotal']:.2f}"
        lines.append(f"{'':<20}{qte:>5}{prix:>8}{total:>9}")

    lines.append("-" * LINE_WIDTH)
    total_str = f"{sale['total']:.2f} DH"
    lines.append(f"{'TOTAL :':<{LINE_WIDTH - len(total_str)}}{total_str}")
    lines.append("-" * LINE_WIDTH)
    lines.append(center("Merci !"))
    lines.append("")
    return "\n".join(lines)


def build_stats_ticket_text(store, title, stats):
    """
    Builds a plain-text ticket (80mm) for statistics — same look and feel
    as the sale receipt (store header, dashed separators, 42 columns).

    stats: dict like the one returned by /api/stats/today (or a month),
           with keys: date|month, totals{in,out,adjust}, products[],
           sales_count, revenue.
    """
    lines = []
    center = lambda s: s.center(LINE_WIDTH)

    lines.append(center(store.get("store_name", "STOCK APP")))
    if store.get("store_address"):
        lines.append(center(store["store_address"]))
    if store.get("store_phone"):
        lines.append(center(store["store_phone"]))
    lines.append("-" * LINE_WIDTH)
    lines.append(center(title))
    label = ""
    if stats.get("date"):
        try:
            dt = datetime.strptime(stats["date"], "%Y-%m-%d")
            label = dt.strftime("%d/%m/%Y")
        except Exception:
            label = stats["date"]
    elif stats.get("month"):
        try:
            y, m = map(int, stats["month"].split("-"))
            label = datetime(y, m, 1).strftime("%m/%Y")
        except Exception:
            label = stats["month"]
    if label:
        lines.append(center(label))
    lines.append("-" * LINE_WIDTH)

    totals = stats.get("totals", {})
    total_in = totals.get("in", 0)
    total_out = totals.get("out", 0)
    # Corrections are already folded into entries (positive) or exits
    # (negative) by the statistics service.
    net = total_in - total_out

    lines.append(f"Entrées     : +{total_in}")
    lines.append(f"Sorties     : -{total_out}")
    net_signed = ("+" if net >= 0 else "") + str(net)
    lines.append(f"Solde       : {net_signed}")
    lines.append("-" * LINE_WIDTH)
    lines.append(f"Ventes : {stats.get('sales_count', 0)}     CA : {stats.get('revenue', 0):.2f} DH")
    lines.append("-" * LINE_WIDTH)

    lines.append(f"{'Produit':<14}{'Ent':>6}{'Sor':>6}{'Solde':>8}")
    lines.append("-" * LINE_WIDTH)

    products = stats.get("products", [])
    if not products:
        lines.append(center("Aucun mouvement"))
    else:
        for p in products:
            name = (p["name"] or "")[:14]
            ent = p.get("in", 0)
            sor = p.get("out", 0)
            np = p.get("net", 0)
            np_signed = ("+" if np >= 0 else "") + str(np)
            lines.append(f"{name:<14}{ent:>6}{sor:>6}{np_signed:>8}")

    lines.append("-" * LINE_WIDTH)
    lines.append(center("Merci !"))
    lines.append("")
    return "\n".join(lines)


def print_stats_ticket(store, title, stats):
    """
    Prints a statistics ticket. Same strategy as the receipt:
      1. Windows-installed printer (raw ESC/POS)
    Returns {"printed": bool, "message": str, "ticket_text": str}.
    """
    ticket_text = build_stats_ticket_text(store, title, stats)
    printer_name = find_windows_printer(store.get("printer_name"))
    if printer_name and print_via_windows(printer_name, ticket_text):
        return {
            "printed": True,
            "message": f"Fiche envoyée à l'imprimante Windows : {printer_name}.",
            "ticket_text": ticket_text,
        }
    return {
        "printed": False,
        "message": "Impression impossible (imprimante non détectée). Ticket généré en mode texte.",
        "ticket_text": ticket_text,
    }


def print_receipt(store, sale, items):
    """
    Attempts to print the receipt, trying (in order):
      1. Direct USB via python-escpos / pyusb
      2. The Windows-installed printer (win32print raw ESC/POS)
    Returns a dict: {"printed": bool, "message": str, "ticket_text": str}
    Never raises — errors are caught and reported so the rest of the
    app keeps working even if the printer is off/unavailable.
    """
    ticket_text = build_receipt_text(store, sale, items)

    Usb = _try_import_escpos()
    if Usb is not None:
        try:
            vendor_id = int(PRINTER_VENDOR_ID, 16)
            product_id = int(PRINTER_PRODUCT_ID, 16)
            printer = Usb(vendor_id, product_id, timeout=0, in_ep=0x82, out_ep=0x01)

            printer.set(align="center", bold=True, width=2, height=2)
            printer.text(store.get("store_name", "STOCK APP") + "\n")
            printer.set(align="center", bold=False, width=1, height=1)
            if store.get("store_address"):
                printer.text(store["store_address"] + "\n")
            if store.get("store_phone"):
                printer.text(store["store_phone"] + "\n")
            printer.text("-" * LINE_WIDTH + "\n")

            printer.set(align="left")
            printer.text(f"Vente : {sale['sale_number']}\n")
            printer.text(f"Date  : {sale.get('created_at', '')}\n")
            printer.text("-" * LINE_WIDTH + "\n")

            for item in items:
                printer.text(f"{item['name']}\n")
                qte = str(item["quantity"])
                prix = f"{item['unit_price']:.2f}"
                total = f"{item['subtotal']:.2f}"
                printer.text(f"{'':<20}{qte:>5}{prix:>8}{total:>9}\n")

            printer.text("-" * LINE_WIDTH + "\n")
            printer.set(bold=True)
            printer.text(f"TOTAL : {sale['total']:.2f} DH\n")
            printer.set(bold=False)
            printer.text("-" * LINE_WIDTH + "\n")
            printer.set(align="center")
            printer.text("Merci !\n\n")

            try:
                printer.cut()
            except Exception:
                pass  # cutter not supported / not needed

            printer.close()
            return {
                "printed": True,
                "message": "Ticket envoyé à l'imprimante WD8260.",
                "ticket_text": ticket_text,
            }
        except Exception:
            pass  # USB direct failed — try the Windows printer below

    # Route 2: send the ticket to the Windows-installed printer (raw ESC/POS)
    printer_name = find_windows_printer(store.get("printer_name"))
    if printer_name and print_via_windows(printer_name, ticket_text):
        return {
            "printed": True,
            "message": f"Ticket envoyé à l'imprimante Windows : {printer_name}.",
            "ticket_text": ticket_text,
        }

    # Final fallback: plain-text ticket (never blocks the app)
    return {
        "printed": False,
        "message": "Impression impossible (imprimante non détectée). "
                   "Ticket généré en mode texte.",
        "ticket_text": ticket_text,
    }
