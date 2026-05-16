import pandas as pd


def load_rooms(path):
    return pd.read_excel(path, engine="openpyxl")

def load_guests(path):
    return pd.read_excel(path, engine="openpyxl")


