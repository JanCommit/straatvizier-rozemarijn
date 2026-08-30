"""Bereid snelheidsdata en tijdlabels voor de verschillende dashboardviews voor."""

import pandas as pd

from straatvizier.database import (
    aggregate_speed_period,
    get_speed_week_profile,
    get_speed_year_profile,
)
from straatvizier.ui.chart_helpers import (
    MONTH_NAMES_NL,
    WEEKDAY_NAMES_NL,
    hour_period_label,
    profile_hour_label,
    month_label,
)


LOCAL_TIMEZONE = "Europe/Brussels"


def valid_daily_speed(
    df,
    min_hours,
):
    """Behoud snelheidsdagen met minstens het vereiste aantal geldige uren."""
    if df.empty:
        return df.copy()

    return df[
        df["hours"] >= min_hours
    ].copy()


def speed_view_data(
    view_name,
    hourly,
    daily,
    hour_profile,
    min_hours,
):
    """Bouw de snelheidstabel die hoort bij de gekozen tijds- of profielweergave."""
    valid = valid_daily_speed(
        daily,
        min_hours,
    )

    if view_name == "Per uur":
        data = hourly.copy()

        if not data.empty:
            data["x"] = (
                data["measured_at"]
                .dt.tz_convert(
                    LOCAL_TIMEZONE
                )
            )

            full_hours = pd.date_range(
                data["x"].min(),
                data["x"].max(),
                freq="h",
                tz=LOCAL_TIMEZONE,
            )

            data = (
                data
                .set_index("x")
                .reindex(full_hours)
                .rename_axis("x")
                .reset_index()
            )

        return data

    if view_name == "Per dag":
        data = valid.copy()

        if not data.empty:
            data["x"] = data["date"]

            full_days = pd.date_range(
                data["x"].min(),
                data["x"].max(),
                freq="D",
            )

            data = (
                data
                .set_index("x")
                .reindex(full_days)
                .rename_axis("x")
                .reset_index()
            )

        return data

    if view_name in {
        "Per week",
        "Per maand",
        "Per jaar",
    }:
        period = {
            "Per week": "week",
            "Per maand": "month",
            "Per jaar": "year",
        }[view_name]

        data = aggregate_speed_period(
            valid,
            period,
        )

        if not data.empty:
            data["x"] = data[period]

            freq = {
                "week": "W-MON",
                "month": "MS",
                "year": "YS",
            }[period]

            full_periods = pd.date_range(
                data["x"].min(),
                data["x"].max(),
                freq=freq,
            )

            data = (
                data
                .set_index("x")
                .reindex(full_periods)
                .rename_axis("x")
                .reset_index()
            )

            if period == "week":
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

                data["week_end"] = (
                    data["x"]
                    + pd.Timedelta(days=6)
                )

                data["week_period"] = data.apply(
                    lambda row: (
                        f"ma {row['x'].day} "
                        f"{month_names[row['x'].month]} – "
                        f"zo {row['week_end'].day} "
                        f"{month_names[row['week_end'].month]} "
                        f"{row['week_end'].year}"
                    )
                    if pd.notna(row["x"])
                    else "",
                    axis=1,
                )

        return data

    if view_name == "24u-profiel":
        data = hour_profile.copy()

        if not data.empty:
            data["x"] = data["hour"]

        return data

    if view_name == "Weekprofiel":
        data = get_speed_week_profile(
            valid
        )

        if not data.empty:
            data["x"] = data["weekday"]

        return data

    data = get_speed_year_profile(
        valid
    )

    if not data.empty:
        data["x"] = (
            data["month_number"]
        )

    return data

def speed_time_hover_data(
    view_name,
    data,
):
    """Maak per snelheidsview de centrale Nederlandse tijdlabels voor unified hover."""
    if data is None or data.empty:
        return pd.DataFrame(
            columns=["x", "label"]
        )

    result = pd.DataFrame(
        {"x": data["x"]}
    )

    if view_name == "Per uur":
        result["label"] = data["x"].apply(
            hour_period_label
        )

    elif view_name == "Per dag":
        result["label"] = (
            pd.to_datetime(data["x"])
            .dt.strftime("%d/%m/%Y")
        )

    elif view_name == "Per week":
        result["label"] = data["week_period"]

    elif view_name == "Per maand":
        result["label"] = data["x"].apply(
            month_label
        )

    elif view_name == "Per jaar":
        result["label"] = (
            pd.to_datetime(data["x"])
            .dt.strftime("%Y")
        )

    elif view_name == "24u-profiel":
        result["label"] = data["x"].apply(
            profile_hour_label
        )

    elif view_name == "Weekprofiel":
        result["label"] = data["x"].apply(
            lambda value:
                WEEKDAY_NAMES_NL[int(value)]
                if pd.notna(value)
                else ""
        )

    else:
        result["label"] = data["x"].apply(
            lambda value:
                MONTH_NAMES_NL[int(value)].capitalize()
                if pd.notna(value)
                else ""
        )

    return result
