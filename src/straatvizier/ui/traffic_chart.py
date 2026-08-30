"""Voeg verkeersseries voor de gekozen tijdsweergave toe aan een Plotly-figuur."""

import pandas as pd
import plotly.graph_objects as go

from straatvizier.analysis import (
    add_missing_days_as_gaps,
    add_rolling_average,
)
from straatvizier.data_helpers import (
    weekly_data,
    monthly_data,
    yearly_data,
    hourly_with_gaps,
)
from straatvizier.ui.chart_helpers import (
    MONTH_ABBR_NL,
    WEEKDAY_ABBR_NL,
)

MAIN_STREET_COLOR = "#1E88E5"
COMPARE_STREET_COLOR = "#80649A"
MAIN_TREND_COLOR = "#E8655B"
COMPARE_TREND_COLOR = "#6F5A8C"


def add_view(
    fig,
    row,
    view,
    street,
    daily,
    valid,
    label,
    min_hours,
    rolling_days,
    show_rolling,
    hourly=None,
    hour_profile=None,
    is_comparison=False,
    series_suffix=None,
    line_dash="solid",
):
    """Voeg de verkeersreeks(en) voor één gekozen dashboardweergave toe."""
    street_color = (
        COMPARE_STREET_COLOR
        if is_comparison
        else MAIN_STREET_COLOR
    )

    trend_color = (
        COMPARE_TREND_COLOR
        if is_comparison
        else MAIN_TREND_COLOR
    )

    if view == "Per uur":
        data = hourly_with_gaps(
            hourly
            if hourly is not None
            else pd.DataFrame()
        )

        if not data.empty:
            fig.add_trace(
                go.Scattergl(
                    x=data["measured_at_local"],
                    y=data["selected_traffic"],
                    mode="lines",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    connectgaps=False,
                    hovertemplate=(
                        (
                            f"{street} · {series_suffix}: "
                            if series_suffix
                            else f"{street}: "
                        )
                        + "%{y:,.0f}"
                        + "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=1.6,
                        dash=line_dash,
                    ),
                ),
                row=row,
                col=1,
            )

        return f"{label} per uur"

    if view == "Per dag":
        data = add_missing_days_as_gaps(
            valid
        )

        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data["value"],
                    mode="lines",
                    name=(f"{street} · {series_suffix} — dagelijks" if series_suffix else f"{street} — dagelijks"),
                    connectgaps=False,
                    hovertemplate=(
                        (
                            f"{street} · {series_suffix}: "
                            if series_suffix
                            else f"{street}: "
                        )
                        + "%{y:,.0f}"
                        + "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=1.5,
                        dash=line_dash,
                    ),
                    opacity=0.68,
                ),
                row=row,
                col=1,
            )

            if show_rolling:
                trend = add_rolling_average(
                    data,
                    window_days=rolling_days,
                )

                fig.add_trace(
                    go.Scatter(
                        x=trend["date"],
                        y=trend["rolling_average"],
                        mode="lines",
                        name=(
                            f"{street}"
                            + (f" · {series_suffix}" if series_suffix else "")
                            + f" — {rolling_days}-daags gemiddelde"
                        ),
                        connectgaps=False,
                        hovertemplate=(
                            (
                                f"{street} · {series_suffix}"
                                if series_suffix
                                else street
                            )
                            + f" — {rolling_days}-daags gemiddelde: "
                            + "%{y:,.0f}"
                            + "<extra></extra>"
                        ),
                        line=dict(
                            color=trend_color,
                            width=3.2,
                            dash=line_dash,
                        ),
                    ),
                    row=row,
                    col=1,
                )

        return f"{label} per dag"

    if view == "Per week":
        data = weekly_data(
            daily,
            min_hours,
        )

        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data["week"],
                    y=data["avg_daily_traffic"],
                    mode="lines+markers",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    connectgaps=False,
                    customdata=data[
                        [
                            "week_period",
                            "sum_valid_traffic",
                            "valid_days",
                            "avg_uptime",
                        ]
                    ],
                    hovertemplate=(
                        "Gemiddeld per geldige dag: "
                        "%{y:,.0f}<br>"
                        "Som over geldige dagen: "
                        "%{customdata[1]:,.0f}<br>"
                        "Geldige dagen: "
                        "%{customdata[2]:.0f}<br>"
                        "Gem. uptime: "
                        "%{customdata[3]:.0%}"
                        "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=2,
                        dash=line_dash,
                    ),
                    marker=dict(
                        size=5,
                        color=street_color,
                    ),
                ),
                row=row,
                col=1,
            )

        return (
            f"Gemiddeld {label.lower()} "
            f"per geldige dag"
        )

    if view == "Per maand":
        data = monthly_data(
            daily,
            min_hours,
        )

        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data["month"],
                    y=data["avg_daily_traffic"],
                    mode="lines+markers",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    connectgaps=False,
                    customdata=data[
                        [
                            "sum_valid_traffic",
                            "valid_days",
                            "avg_uptime",
                        ]
                    ],
                    hovertemplate=(
                        "Gemiddeld per geldige dag: "
                        "%{y:,.0f}<br>"
                        "Som over geldige dagen: "
                        "%{customdata[0]:,.0f}<br>"
                        "Geldige dagen: "
                        "%{customdata[1]:.0f}<br>"
                        "Gem. uptime: "
                        "%{customdata[2]:.0%}"
                        "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=2,
                        dash=line_dash,
                    ),
                    marker=dict(
                        size=6,
                        color=street_color,
                    ),
                ),
                row=row,
                col=1,
            )

        return (
            f"Gemiddeld {label.lower()} "
            f"per geldige dag"
        )

    if view == "Per jaar":
        data = yearly_data(
            daily,
            min_hours,
        )

        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data["year"],
                    y=data["avg_daily_traffic"],
                    mode="lines+markers",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    connectgaps=False,
                    xhoverformat="%Y",
                    customdata=data[
                        [
                            "sum_valid_traffic",
                            "valid_days",
                            "calendar_days",
                            "coverage",
                            "avg_uptime",
                        ]
                    ],
                    hovertemplate=(
                        "Gemiddeld per geldige dag: "
                        "%{y:,.0f}<br>"
                        "Som over geldige dagen: "
                        "%{customdata[0]:,.0f}<br>"
                        "Geldige dagen: "
                        "%{customdata[1]:.0f} / "
                        "%{customdata[2]:.0f}<br>"
                        "Dekking: "
                        "%{customdata[3]:.1%}<br>"
                        "Gem. uptime: "
                        "%{customdata[4]:.0%}"
                        "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=2.4,
                        dash=line_dash,
                    ),
                    marker=dict(
                        size=8,
                        color=street_color,
                    ),
                ),
                row=row,
                col=1,
            )

        return (
            f"Gemiddeld {label.lower()} "
            f"per geldige dag"
        )

    if view == "24u-profiel":
        data = (
            hour_profile
            if hour_profile is not None
            else pd.DataFrame()
        )

        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data["hour"],
                    y=data["avg_traffic"],
                    mode="lines+markers",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    hovertemplate=(
                        (
                            f"{street} · {series_suffix}: "
                            if series_suffix
                            else f"{street}: "
                        )
                        + "%{y:,.0f}"
                        + "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=2.5,
                        dash=line_dash,
                    ),
                    marker=dict(
                        color=street_color,
                    ),
                ),
                row=row,
                col=1,
            )

            fig.update_xaxes(
                dtick=1,
                row=row,
                col=1,
            )

        return f"Gemiddeld {label.lower()}"

    if view == "Weekprofiel":
        data = valid.copy()

        if not data.empty:
            data["weekday"] = (
                data["date"].dt.weekday
            )

            data = (
                data
                .groupby(
                    "weekday",
                    as_index=False,
                )
                .agg(
                    avg=("value", "mean"),
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=data["weekday"],
                    y=data["avg"],
                    mode="lines+markers",
                    name=(f"{street} · {series_suffix}" if series_suffix else street),
                    hovertemplate=(
                        (
                            f"{street} · {series_suffix}: "
                            if series_suffix
                            else f"{street}: "
                        )
                        + "%{y:,.0f}"
                        + "<extra></extra>"
                    ),
                    line=dict(
                        color=street_color,
                        width=2.5,
                        dash=line_dash,
                    ),
                    marker=dict(
                        color=street_color,
                    ),
                ),
                row=row,
                col=1,
            )

            fig.update_xaxes(
                tickmode="array",
                tickvals=list(range(7)),
                ticktext=WEEKDAY_ABBR_NL,
                row=row,
                col=1,
            )

        return (
            f"Gemiddeld {label.lower()} "
            f"per dag"
        )

    data = valid.copy()

    if not data.empty:
        data["month_number"] = (
            data["date"].dt.month
        )

        data = (
            data
            .groupby(
                "month_number",
                as_index=False,
            )
            .agg(
                avg=("value", "mean"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data["month_number"],
                y=data["avg"],
                mode="lines+markers",
                name=(f"{street} · {series_suffix}" if series_suffix else street),
                hovertemplate=(
                    (
                        f"{street} · {series_suffix}: "
                        if series_suffix
                        else f"{street}: "
                    )
                    + "%{y:,.0f}"
                    + "<extra></extra>"
                ),
                line=dict(
                    color=street_color,
                    width=2.5,
                    dash=line_dash,
                ),
                marker=dict(
                    color=street_color,
                ),
            ),
            row=row,
            col=1,
        )

        fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[
                MONTH_ABBR_NL[index]
                for index in range(1, 13)
            ],
            row=row,
            col=1,
        )

    return (
        f"Gemiddeld {label.lower()} "
        f"per dag"
    )
