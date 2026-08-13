def normalize_scan_code(value):
    """Normalize a scanned code and ensure it only contains digits."""
    if value is None:
        raise ValueError("Le code scanné est vide.")

    code = str(value).strip()
    if not code:
        raise ValueError("Le code scanné est vide.")
    if not code.isdigit():
        raise ValueError("Le code scanné ne doit contenir que des chiffres.")
    return code
