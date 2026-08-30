"""Helpers die verkeersaggregaten omvormen tot complete grafiekreeksen, met expliciete gaten voor ontbrekende perioden."""

import pandas as pd

from straatvizier.analysis import (
    weekly_average_daily_traffic,
    monthly_average_daily_traffic,
    yearly_average_daily_traffic,
)

LOCAL_TIMEZONE = "Europe/Brussels"


def valid_daily(daily_df, min_hours):
    """Behoud alleen dagen met minstens min_hours geldige meeturen."""
    if daily_df.empty:
        return daily_df.copy()

    return daily_df[
        daily_df["hours"] >= min_hours
    ].copy()

def weighted_avg_uptime(daily_df):
    """Bereken gemiddelde uptime gewogen volgens het aantal geldige meeturen."""
    if daily_df.empty:
        return None

    hours = daily_df["hours"].sum()

    if not hours:
        return None

    return (
        (
            daily_df["avg_uptime"]
            * daily_df["hours"]
        ).sum()
        / hours
    )

def weekly_data(daily_df, min_hours):
    """Maak weekaggregaten en voeg ontbrekende kalenderweken als gaten toe."""
    result = weekly_average_daily_traffic(
        daily_df,
        min_hours_per_day=min_hours,
    )

    if result.empty:
        return result

    result = result.copy()
    result["week"] = pd.to_datetime(
        result["week"]
    )

    full_weeks = pd.date_range(
        result["week"].min(),
        result["week"].max(),
        freq="W-MON",
    )

    result = (
        result
        .set_index("week")
        .reindex(full_weeks)
        .rename_axis("week")
        .reset_index()
    )

    month_names = {
        1: "jan",
        2: "feb",
        3: "mrt",
        4: "apr",
        5: "mei",
        6: "jun",
        7: "jul",
        8: "aug",
        9: "sep",
        10: "okt",
        11: "nov",
        12: "dec",
    }

    result["week_end"] = (
        result["week"]
        + pd.Timedelta(days=6)
    )

    result["week_period"] = result.apply(
        lambda row: (
            f"ma {row['week'].day} "
            f"{month_names[row['week'].month]} – "
            f"zo {row['week_end'].day} "
            f"{month_names[row['week_end'].month]} "
            f"{row['week_end'].year}"
        )
        if pd.notna(row["week"])
        else "",
        axis=1,
    )

    return result

def monthly_data(daily_df, min_hours):
    """Maak maandaggregaten en voeg ontbrekende maanden als gaten toe."""
    result = monthly_average_daily_traffic(
        daily_df,
        min_hours_per_day=min_hours,
    )

    if result.empty:
        return result

    result = result.copy()

    result["month"] = pd.to_datetime(
        result["month"]
    )

    full_months = pd.date_range(
        result["month"].min(),
        result["month"].max(),
        freq="MS",
    )

    return (
        result
        .set_index("month")
        .reindex(full_months)
        .rename_axis("month")
        .reset_index()
    )

def yearly_data(daily_df, min_hours):
    """Maak jaaraggregaten en voeg ontbrekende jaren als gaten toe."""
    result = yearly_average_daily_traffic(
        daily_df,
        min_hours_per_day=min_hours,
    )

    if result.empty:
        return result

    result = result.copy()
    result["year"] = pd.to_datetime(result["year"])

    full_years = pd.date_range(
        result["year"].min(),
        result["year"].max(),
        freq="YS",
    )

    return (
        result
        .set_index("year")
        .reindex(full_years)
        .rename_axis("year")
        .reset_index()
    )

def hourly_with_gaps(hourly_df):
    """Maak een volledige lokale uurindex zodat ontbrekende uren zichtbaar blijven."""
    if hourly_df.empty:
        return hourly_df.copy()

    result = hourly_df.copy()

    result["measured_at_local"] = (
        result["measured_at"]
        .dt.tz_convert(LOCAL_TIMEZONE)
    )

    result = result.sort_values(
        "measured_at_local"
    )

    # Een volledige uurindex maakt meetgaten expliciet als NaN, zodat Plotly
    # geen misleidende lijn over ontbrekende uren tekent.
    full_range = pd.date_range(
        result["measured_at_local"].min(),
        result["measured_at_local"].max(),
        freq="h",
        tz=LOCAL_TIMEZONE,
    )

    return (
        result
        .set_index("measured_at_local")
        .reindex(full_range)
        .rename_axis("measured_at_local")
        .reset_index()
    )

