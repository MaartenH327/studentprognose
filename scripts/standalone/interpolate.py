import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import os

path_cumulative = "//ru.nl/wrkgrp/TeamIR/Man_info/Student Analytics/Prognosemodel RU/Syntax/Python/studentprognose/data/input/vooraanmeldingen_cumulatief.csv"
data_cumulative = (
    pd.read_csv(path_cumulative, sep=";", low_memory=True)
    if (path_cumulative != "" and os.path.exists(path_cumulative))
    else None
)


def convert_to_float(value):
    if isinstance(value, str):
        # Remove thousand separator (dot) and replace decimal separator (comma) with a dot
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def convert_other_columns(value):
    if isinstance(value, str):
        value = value.replace(".", "").replace(",", ".")
    return float(value)


# Preprocess numeric columns
data_cumulative["Gewogen vooraanmelders"] = data_cumulative["Gewogen vooraanmelders"].apply(
    convert_to_float
)
for col in ["Ongewogen vooraanmelders", "Aantal aanmelders met 1 aanmelding", "Inschrijvingen"]:
    data_cumulative[col] = data_cumulative[col].apply(convert_other_columns)


def week_position(week, start_week, is_wrap, max_week):
    """
    Converts a given week number to a position relative to start_week.
    If is_wrap is True (i.e. start_week > end_week), weeks less than start_week
    are adjusted by adding (max_week - start_week + 1).
    """
    if not is_wrap:
        return week - start_week
    else:
        if week >= start_week:
            return week - start_week
        else:
            return week + (max_week - start_week + 1)


def interpolate(data, year, start_week, end_week, max_week=52):
    """
    Interpolates values for intermediate weeks between specified start_week and end_week for a given academic year.
    The function filters the data (for non-repeat, non-higher-year students and specific origin groups),
    computes a linear interpolation for each (croho, herkomst) group and target column,
    and then merges the interpolated values back into the original dataframe.

    Parameters:
        data (DataFrame): Input DataFrame.
        year (int): The academic year to filter on.
        start_week (int): The starting endpoint week for interpolation.
        end_week (int): The ending endpoint week for interpolation.
        max_week (int): The maximum week number (default is 52).

    Returns:
        DataFrame: Updated DataFrame with interpolated values for intermediate weeks.
    """
    is_wrap = start_week > end_week

    # Filter data for the given year, the endpoint weeks, and required conditions
    filtered_data = data[
        (data["Herinschrijving"] == "Nee")
        & (data["Hogerejaars"] == "Nee")
        & (data.Collegejaar == year)
        & (data.Weeknummer.isin([start_week, end_week]))  # &
        # (data.Herkomst.isin(["Niet-EER", "EER"]))
    ]

    # Determine which weeks lie between the endpoints.
    if not is_wrap:
        intermediate_weeks = list(range(start_week + 1, end_week))
    else:
        # Wrap-around: weeks from start_week+1 to max_week, then from 1 to end_week-1
        intermediate_weeks = list(range(start_week + 1, max_week + 1)) + list(range(1, end_week))

    def interpolate_single_week(croho, herkomst, examentype, target_value):
        group_data = filtered_data[
            (filtered_data["Groepeernaam Croho"] == croho)
            & (filtered_data.Herkomst == herkomst)
            & (filtered_data["Type hoger onderwijs"] == examentype)
        ]
        value_start_series = group_data[group_data.Weeknummer == start_week][target_value]
        value_end_series = group_data[group_data.Weeknummer == end_week][target_value]
        if not value_start_series.empty and not value_end_series.empty:
            wk_start_value = convert_to_float(value_start_series.iloc[0])
            wk_end_value = convert_to_float(value_end_series.iloc[0])
            pos_start = 0
            pos_end = week_position(end_week, start_week, is_wrap, max_week)
            # Create a linear interpolator based on relative positions
            interpolator = interp1d(
                [pos_start, pos_end], [wk_start_value, wk_end_value], kind="linear"
            )
            # Calculate positions for each intermediate week
            positions = [
                week_position(week, start_week, is_wrap, max_week) for week in intermediate_weeks
            ]
            return interpolator(positions)
        return None

    # Collect interpolated values for each group and target column
    updates = {
        "Collegejaar": [],
        "Weeknummer": [],
        "Type hoger onderwijs": [],
        "Groepeernaam Croho": [],
        "Herkomst": [],
        "target_value": [],
        "value": [],
    }

    croho_herkomst_groups = filtered_data[
        ["Type hoger onderwijs", "Groepeernaam Croho", "Herkomst"]
    ].drop_duplicates()

    for _, group in croho_herkomst_groups.iterrows():
        croho = group["Groepeernaam Croho"]
        herkomst = group["Herkomst"]
        examentype = group["Type hoger onderwijs"]
        for target_value in [
            "Gewogen vooraanmelders",
            "Ongewogen vooraanmelders",
            "Aantal aanmelders met 1 aanmelding",
            "Inschrijvingen",
        ]:
            interpolated_values = interpolate_single_week(
                croho, herkomst, examentype, target_value
            )
            if interpolated_values is not None:
                for week, interp_val in zip(intermediate_weeks, interpolated_values):
                    updates["Collegejaar"].append(year)
                    updates["Weeknummer"].append(week)
                    updates["Type hoger onderwijs"].append(examentype)
                    updates["Groepeernaam Croho"].append(croho)
                    updates["Herkomst"].append(herkomst)
                    updates["target_value"].append(target_value)
                    updates["value"].append(interp_val)

    # Pivot the updates into wide format and merge with the original data
    updates_df = pd.DataFrame(updates)
    updates_pivot = updates_df.pivot_table(
        index=[
            "Collegejaar",
            "Weeknummer",
            "Type hoger onderwijs",
            "Groepeernaam Croho",
            "Herkomst",
        ],
        columns="target_value",
        values="value",
    ).reset_index()

    data_updated = data.merge(
        updates_pivot,
        on=["Collegejaar", "Weeknummer", "Type hoger onderwijs", "Groepeernaam Croho", "Herkomst"],
        how="left",
        suffixes=("", "_interpolated"),
    )

    # Replace values with the interpolated ones when available
    for col in [
        "Gewogen vooraanmelders",
        "Ongewogen vooraanmelders",
        "Aantal aanmelders met 1 aanmelding",
        "Inschrijvingen",
    ]:
        data_updated[col] = data_updated[f"{col}_interpolated"].combine_first(data_updated[col])

    data_updated.drop(
        columns=[
            f"{col}_interpolated"
            for col in [
                "Gewogen vooraanmelders",
                "Ongewogen vooraanmelders",
                "Aantal aanmelders met 1 aanmelding",
                "Inschrijvingen",
            ]
        ],
        inplace=True,
    )

    return data_updated


# Example usage:
# Interpolate between weeks 31 and 34 for academic year 2024:
# data_cumulative_met_interpolate = interpolate(data_cumulative, year=2024, start_week=31, end_week=34, max_week=52)

# To interpolate between weeks 51 and 1 (wrap-around), simply call:
data_cumulative_met_interpolate = interpolate(
    data_cumulative, year=2024, start_week=51, end_week=1, max_week=52
)

# Rounding the results as before
data_cumulative_met_interpolate["Gewogen vooraanmelders"] = data_cumulative_met_interpolate[
    "Gewogen vooraanmelders"
].round(2)
columns_to_round = [
    "Ongewogen vooraanmelders",
    "Aantal aanmelders met 1 aanmelding",
    "Inschrijvingen",
]
for col in columns_to_round:
    data_cumulative_met_interpolate[col] = data_cumulative_met_interpolate[col].where(
        data_cumulative_met_interpolate[col].notna(), np.nan
    )
    data_cumulative_met_interpolate[col] = np.round(data_cumulative_met_interpolate[col]).astype(
        "Int64"
    )

data_cumulative_met_interpolate.to_csv(
    "//ru.nl/wrkgrp/TeamIR/Man_info/Student Analytics/Prognosemodel RU/Syntax/Python/studentprognose/data/input/vooraanmeldingen_cumulatief.csv",
    sep=";",
    index=False,
)
