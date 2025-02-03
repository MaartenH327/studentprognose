import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.load_data import load_configuration

if __name__ == "__main__":
    configuration = load_configuration("configuration/configuration.json")

    data = pd.read_excel(configuration["paths"]["path_latest"])

    data["Higher_years_prediction"] = data["Higher_years_prediction_CurrentYear"]

    data["Volume_prediction"] = data["Higher_years_prediction"] + data["Ensemble_prediction"]

    data["MAE_higher_years"] = data["MAE_higher_years_CurrentYear"]

    data["MAE_volume"] = abs(data["Volume_prediction"] - data["Aantal_studenten_volume"])

    data["MAPE_higher_years"] = data["MAPE_higher_years_CurrentYear"]

    data["MAPE_volume"] = (
        abs(data["Volume_prediction"] - data["Aantal_studenten_volume"])
        / data["Aantal_studenten_volume"]
    )

    data.to_excel("totaal.xlsx", index=False)
