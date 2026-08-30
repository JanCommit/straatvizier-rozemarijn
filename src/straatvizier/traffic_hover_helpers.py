"""Bouw de centrale Nederlandse tijdsaanduiding voor verkeers-hoverlabels."""

import pandas as pd

from straatvizier.analysis import add_missing_days_as_gaps
from straatvizier.data_helpers import (
    weekly_data,
    monthly_data,
    yearly_data,
    hourly_with_gaps,
)
from straatvizier.ui.chart_helpers import (
    MONTH_NAMES_NL,
    WEEKDAY_NAMES_NL,
    hour_period_label,
    profile_hour_label,
    month_label,
)


# Deze helper levert alleen tijdcontext; zichtbare traces leveren de waarden.
def traffic_time_hover_data(
    view_name,
    daily,
    valid,
    hourly=None,
    hour_profile=None,
    min_hours=None,
):
    """Geef per view de x-posities en Nederlandse tijdlabels voor unified hover."""
    if view_name == "Per uur":
        data = hourly_with_gaps(
            hourly
            if hourly is not None
            else pd.DataFrame()
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["measured_at_local"],
                "label": data[
                    "measured_at_local"
                ].apply(hour_period_label),
            }
        )

    if view_name == "Per dag":
        data = add_missing_days_as_gaps(
            valid
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["date"],
                "label": pd.to_datetime(
                    data["date"]
                ).dt.strftime("%d/%m/%Y"),
            }
        )

    if view_name == "Per week":
        data = weekly_data(
            daily,
            min_hours,
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["week"],
                "label": data["week_period"],
            }
        )

    if view_name == "Per maand":
        data = monthly_data(
            daily,
            min_hours,
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["month"],
                "label": data["month"].apply(
                    month_label
                ),
            }
        )

    if view_name == "Per jaar":
        data = yearly_data(
            daily,
            min_hours,
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["year"],
                "label": pd.to_datetime(
                    data["year"]
                ).dt.strftime("%Y"),
            }
        )

    if view_name == "24u-profiel":
        data = (
            hour_profile
            if hour_profile is not None
            else pd.DataFrame()
        )

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        return pd.DataFrame(
            {
                "x": data["hour"],
                "label": data["hour"].apply(
                    profile_hour_label
                ),
            }
        )

    if view_name == "Weekprofiel":
        data = valid.copy()

        if data.empty:
            return pd.DataFrame(
                columns=["x", "label"]
            )

        weekdays = (
            data["date"]
            .dt.weekday
            .drop_duplicates()
            .sort_values()
        )

        return pd.DataFrame(
            {
                "x": weekdays,
                "label": weekdays.apply(
                    lambda value:
                        WEEKDAY_NAMES_NL[int(value)]
                ),
            }
        )

    data = valid.copy()

    if data.empty:
        return pd.DataFrame(
            columns=["x", "label"]
        )

    months = (
        data["date"]
        .dt.month
        .drop_duplicates()
        .sort_values()
    )

    return pd.DataFrame(
        {
            "x": months,
            "label": months.apply(
                lambda value:
                    MONTH_NAMES_NL[int(value)].capitalize()
            ),
        }
    )
