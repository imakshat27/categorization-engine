ENTITY_TYPES = {

    # =====================================
    # TRAVEL
    # =====================================

    "IRCTC": "TRAVEL",

    "MAKEMYTRIP": "TRAVEL",

    "YATRA": "TRAVEL",


    # =====================================
    # E-COMMERCE
    # =====================================

    "AMAZON": "E-COMMERCE",

    "FLIPKART": "E-COMMERCE",


    # =====================================
    # INSURANCE
    # =====================================

    "LIC": "INSURANCE",


    # =====================================
    # RECHARGE
    # =====================================

    "AIRTEL": "RECHARGE",

    "JIO": "RECHARGE",


    # =====================================
    # UTILITY
    # =====================================

    "BESCOM": "UTILITY"
}

def detect_entity_type(entity_name):

    entity_name = entity_name.upper()


    for entity_keyword, entity_type in ENTITY_TYPES.items():

        if entity_keyword in entity_name:

            return {

                "entity_type": entity_type,

                "entity_confidence": 0.90,

                "matched_entity_rule": entity_keyword
            }


    return {

        "entity_type": "UNKNOWN",

        "entity_confidence": 0.0,

        "matched_entity_rule": "NO_ENTITY_MATCH"
    }