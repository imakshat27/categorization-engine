import re


def parse_upi_transaction(narration):

    result = {
        "entity_name": "UNKNOWN",
        "upi_id": "UNKNOWN",
        "upi_handle": "UNKNOWN"
    }

    # split narration
    parts = narration.split("/")


    # =========================
    # ENTITY EXTRACTION
    # =========================

    # usually second token
    if len(parts) >= 2:

        entity = parts[1].strip()

        # avoid empty values
        if entity:
            result["entity_name"] = entity


    # =========================
    # UPI ID EXTRACTION
    # =========================

    # regex for UPI IDs
    upi_pattern = r'[\w\.-]+@[\w]+'


    match = re.search(
        upi_pattern,
        narration
    )


    if match:

        upi_id = match.group()

        result["upi_id"] = upi_id


        # extract handle
        handle = upi_id.split("@")[1]

        result["upi_handle"] = handle.upper()


    return result