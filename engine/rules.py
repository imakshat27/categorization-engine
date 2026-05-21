import json


def load_category_rules():

    with open("rules/category_rules.json", "r") as file:

        rules = json.load(file)

    return rules

def load_mode_rules():

    with open("rules/mode_rules.json", "r") as file:

        rules = json.load(file)

    return rules

def load_merchant_rules():

    with open("rules/merchant_rules.json", "r") as file:

        rules = json.load(file)

    return rules