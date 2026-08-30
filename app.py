from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

UI_PRIMARY = "#2E6F8E"
MAIN_STREET_COLOR = "#1E88E5"
COMPARE_STREET_COLOR = "#80649A"
MAIN_TREND_COLOR = "#E8655B"
COMPARE_TREND_COLOR = "#6F5A8C"
GRID_COLOR = "#D1D8DE"
AXIS_TEXT_COLOR = "#3F4B55"
SUBPLOT_TITLE_COLOR = "#365F6B"
IVORY = "#F4F1E8"
SAGE = "#C7D0C2"

LOCAL_TIMEZONE = "Europe/Brussels"
APP_VERSION = "0.8.23"

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from straatvizier.analysis import (
    MODES,
    weekly_average_daily_traffic,
    monthly_average_daily_traffic,
    yearly_average_daily_traffic,
    add_missing_days_as_gaps,
    add_rolling_average,
)

from straatvizier.database import (
    get_streets,
    get_measurement_bounds,
    get_daily_traffic,
    get_hourly_traffic,
    get_hour_profile,
    get_hourly_speed,
    get_daily_speed,
    aggregate_speed_period,
    get_speed_hour_profile,
    get_speed_week_profile,
    get_speed_year_profile,
)

from straatvizier.ui.chart_helpers import (
    MONTH_NAMES_NL,
    MONTH_ABBR_NL,
    WEEKDAY_ABBR_NL,
    WEEKDAY_NAMES_NL,
    hour_period_label,
    profile_hour_label,
    month_label,
    add_time_hover_carrier,
)

from straatvizier.ui.header import render_frozen_header

from straatvizier.data_helpers import (
    valid_daily,
    weighted_avg_uptime,
    weekly_data,
    monthly_data,
    yearly_data,
    hourly_with_gaps,
)

from straatvizier.traffic_helpers import (
    requested_directions,
    traffic_label_for,
    mode_flags,
)

from straatvizier.traffic_hover_helpers import (
    traffic_time_hover_data,
)

from straatvizier.segment_config import (
    direction_label,
    sensor_history_label,
)

from straatvizier.speed_helpers import (
    speed_view_data,
    speed_time_hover_data,
)


st.set_page_config(
    page_title="StraatVizier",
    page_icon="🚦",
    layout="wide",
)


# ============================================================
# Cache
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_streets():
    return get_streets()


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_bounds(segment_id: int):
    return get_measurement_bounds(segment_id)


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_daily(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
):
    return get_daily_traffic(
        segment_id=segment_id,
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour,
        min_uptime=min_uptime,
        direction=direction,
        include_car=include_car,
        include_bike=include_bike,
        include_heavy=include_heavy,
        include_pedestrian=include_pedestrian,
    )


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_hourly(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
):
    return get_hourly_traffic(
        segment_id=segment_id,
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour,
        min_uptime=min_uptime,
        direction=direction,
        include_car=include_car,
        include_bike=include_bike,
        include_heavy=include_heavy,
        include_pedestrian=include_pedestrian,
    )


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_hour_profile(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
):
    return get_hour_profile(
        segment_id=segment_id,
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour,
        min_uptime=min_uptime,
        direction=direction,
        include_car=include_car,
        include_bike=include_bike,
        include_heavy=include_heavy,
        include_pedestrian=include_pedestrian,
    )



@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_hourly_speed(
    segment_id,
    start_date,
    end_date,
    start_hour,
    end_hour,
    min_uptime,
):
    return get_hourly_speed(
        segment_id,
        start_date,
        end_date,
        start_hour,
        end_hour,
        min_uptime,
    )


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_daily_speed(
    segment_id,
    start_date,
    end_date,
    start_hour,
    end_hour,
    min_uptime,
):
    return get_daily_speed(
        segment_id,
        start_date,
        end_date,
        start_hour,
        end_hour,
        min_uptime,
    )


@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def cached_get_speed_hour_profile(
    segment_id,
    start_date,
    end_date,
    start_hour,
    end_hour,
    min_uptime,
):
    return get_speed_hour_profile(
        segment_id,
        start_date,
        end_date,
        start_hour,
        end_hour,
        min_uptime,
    )


def valid_daily_speed(
    df,
    min_hours,
):
    if df.empty:
        return df.copy()

    return df[
        df["hours"] >= min_hours
    ].copy()


def add_speed_traces(
    fig,
    row,
    data,
    street,
    is_comparison=False,
):
    if data is None or data.empty:
        return

    base = (
        COMPARE_STREET_COLOR
        if is_comparison
        else MAIN_STREET_COLOR
    )

    trend = (
        COMPARE_TREND_COLOR
        if is_comparison
        else MAIN_TREND_COLOR
    )

    # In unified hover toont alleen V50 de gedeelde metadata.
    # Zo worden periode en aantal auto's slechts één keer vermeld.
    speed_customdata = data[["cars"]]

    v50_hover = (
        "V50: %{y:.1f} km/u"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v50"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V50",
            line=dict(
                color=base,
                width=2,
            ),
            marker=dict(
                size=4,
                color=base,
            ),
            customdata=speed_customdata,
            hovertemplate=v50_hover,
        ),
        row=row,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v85"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V85",
            line=dict(
                color=trend,
                width=2.8,
            ),
            marker=dict(
                size=4,
                color=trend,
            ),
            hovertemplate=(
                "V85: %{y:.1f} km/u"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v95"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V95",
            line=dict(
                color=base,
                width=1.5,
                dash="dash",
            ),
            marker=dict(
                size=4,
                color=base,
            ),
            hovertemplate=(
                "V95: %{y:.1f} km/u"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=1,
    )


    metadata_hover = (
        "Auto's in verdeling: %{customdata[0]:,.0f}"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v50"],
            mode="markers",
            marker=dict(
                size=0.1,
                opacity=0,
            ),
            showlegend=False,
            customdata=speed_customdata,
            hovertemplate=metadata_hover,
        ),
        row=row,
        col=1,
    )


# ============================================================
# Helpers
# ============================================================

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


# ============================================================
# Straten en globale filters
# ============================================================

streets = cached_get_streets()

if streets.empty:
    st.error(
        "Geen straten gevonden in Supabase."
    )
    st.stop()

streets = (
    streets
    .sort_values("street")
    .reset_index(drop=True)
)

street_names = streets["street"].tolist()

default_index = (
    street_names.index("Rozemarijnstraat")
    if "Rozemarijnstraat" in street_names
    else 0
)

st.sidebar.header("Filters")

selected_street = st.sidebar.selectbox(
    "Straat",
    street_names,
    index=default_index,
)

compare = st.sidebar.checkbox(
    "Vergelijk met tweede straat",
    value=False,
)

comparison_street = None
comparison_layout = "Onder elkaar"

if compare:
    comparison_street = st.sidebar.selectbox(
        "Tweede straat",
        [
            street
            for street in street_names
            if street != selected_street
        ],
    )

    comparison_layout = st.sidebar.radio(
        "Vergelijkingsweergave",
        [
            "Onder elkaar",
            "Samen in één grafiek",
        ],
        index=0,
        help=(
            "Onder elkaar toont elke straat apart. "
            "Samen in één grafiek maakt absolute verschillen "
            "tussen beide straten direct zichtbaar."
        ),
    )

    st.sidebar.caption(
        "Filters gelden voor beide straten."
    )

main_sensor_history = sensor_history_label(
    selected_street
)

if main_sensor_history:
    st.sidebar.caption(
        f"Sensor {selected_street}: "
        f"{main_sensor_history}"
    )

if compare:
    comparison_sensor_history = (
        sensor_history_label(
            comparison_street
        )
    )

    if comparison_sensor_history:
        st.sidebar.caption(
            f"Sensor {comparison_street}: "
            f"{comparison_sensor_history}"
        )


analysis_type = st.sidebar.radio(
    "Analyse",
    ["Verkeersaantallen", "Autosnelheid"],
    index=0,
)

if analysis_type == "Verkeersaantallen":
    mode_labels = st.sidebar.multiselect(
        "Vervoersmiddelen",
        list(MODES.keys()),
        default=[
            "Auto's",
            "Zwaar verkeer",
        ],
    )

    if not mode_labels:
        st.warning(
            "Selecteer minstens één vervoersmiddel."
        )
        st.stop()

    selected_modes = [
        MODES[label]
        for label in mode_labels
    ]

    traffic_label = traffic_label_for(
        mode_labels
    )

    direction_choice = st.sidebar.radio(
        "Richting",
        [
            "Beide richtingen",
            "A → B",
            "B → A",
            "Richtingen apart tonen",
        ],
        index=0,
        help=(
            "Telraam-segmentdata gebruiken een vaste oriëntatie: "
            "A → B komt overeen met de opgeslagen *_left-waarden en "
            "B → A met *_right. StraatVizier toont per straat ook "
            "een herkenbaar geografisch richtingslabel."
        ),
    )

    directions = requested_directions(
        direction_choice
    )

    if direction_choice in {
        "A → B",
        "B → A",
    }:
        code = (
            "ab"
            if direction_choice == "A → B"
            else "ba"
        )

        st.sidebar.caption(
            f"{selected_street}: "
            f"{direction_label(selected_street, code)}"
        )

        if compare:
            st.sidebar.caption(
                f"{comparison_street}: "
                f"{direction_label(comparison_street, code)}"
            )

    if direction_choice == "Richtingen apart tonen":
        st.sidebar.caption(
            f"{selected_street}: "
            f"{direction_label(selected_street, 'ab')} · "
            f"{direction_label(selected_street, 'ba')}"
        )

        if compare:
            st.sidebar.caption(
                f"{comparison_street}: "
                f"{direction_label(comparison_street, 'ab')} · "
                f"{direction_label(comparison_street, 'ba')}"
            )

else:
    mode_labels = ["Auto's"]
    selected_modes = ["car"]
    traffic_label = "Autosnelheid"
    direction_choice = "Beide richtingen"
    directions = ["both"]

    st.sidebar.caption(
        "Snelheid is alleen beschikbaar voor auto's "
        "en niet per rijrichting."
    )

start_hour, end_hour = st.sidebar.slider(
    "Uren",
    min_value=0,
    max_value=24,
    value=(8, 18),
    step=1,
    help=(
        "Andere uren kiezen wordt op aanvraag "
        "opnieuw berekend. Bij een lange periode "
        "kan dit iets langer duren."
    ),
)

if (start_hour, end_hour) != (8, 18):
    st.sidebar.caption(
        "ⓘ Aangepaste uren: gegevens worden "
        "opnieuw server-side berekend."
    )

uptime_pct = st.sidebar.slider(
    "Minimum uptime per uur",
    min_value=0,
    max_value=100,
    value=50,
    step=5,
    help=(
        "Telraam corrigeert de uurwaarde al voor de effectieve "
        "teltijd (uptime). StraatVizier corrigeert niet opnieuw. "
        "Uren onder deze grens worden volledig uitgesloten."
    ),
)

min_uptime = uptime_pct / 100

max_hours = max(
    1,
    end_hour - start_hour,
)

min_hours = st.sidebar.slider(
    "Minimum geldige uren per dag",
    min_value=1,
    max_value=max_hours,
    value=min(
        8,
        max_hours,
    ),
    help=(
        "Een kalenderdag wordt alleen meegenomen in dag-, week-, "
        "maand- en jaaranalyses als minstens dit aantal meeturen "
        "de gekozen uptimegrens haalt."
    ),
)

y_axis_from_zero = st.sidebar.checkbox(
    "Y-as vanaf 0",
    value=True,
    help=(
        "Toon de volledige schaal vanaf nul om "
        "absolute verkeersvolumes beter te beoordelen."
    ),
)


st.sidebar.divider()
st.sidebar.caption(f"StraatVizier v{APP_VERSION}")


# ============================================================
# Segmenten en beschikbare periodes
# ============================================================

main_row = streets[
    streets["street"] == selected_street
].iloc[0]

main_id = int(
    main_row["segment_id"]
)

with st.spinner(
    "Beschikbare periode laden..."
):
    main_first_utc, main_last_utc = (
        cached_get_bounds(main_id)
    )

if (
    main_first_utc is None
    or main_last_utc is None
):
    st.warning(
        "Voor deze straat zijn geen metingen gevonden."
    )
    st.stop()

main_first = (
    main_first_utc
    .tz_convert(LOCAL_TIMEZONE)
    .date()
)

main_last = (
    main_last_utc
    .tz_convert(LOCAL_TIMEZONE)
    .date()
)

comparison_id = None
comparison_first = None
comparison_last = None

if compare:
    comparison_row = streets[
        streets["street"]
        == comparison_street
    ].iloc[0]

    comparison_id = int(
        comparison_row["segment_id"]
    )

    with st.spinner(
        "Beschikbare periode vergelijkingsstraat laden..."
    ):
        (
            comparison_first_utc,
            comparison_last_utc,
        ) = cached_get_bounds(
            comparison_id
        )

    if (
        comparison_first_utc is None
        or comparison_last_utc is None
    ):
        st.warning(
            "Voor de tweede straat zijn "
            "geen metingen gevonden."
        )
        st.stop()

    comparison_first = (
        comparison_first_utc
        .tz_convert(LOCAL_TIMEZONE)
        .date()
    )

    comparison_last = (
        comparison_last_utc
        .tz_convert(LOCAL_TIMEZONE)
        .date()
    )


period_min = min(
    date
    for date in [
        main_first,
        comparison_first,
    ]
    if date is not None
)

period_max = max(
    date
    for date in [
        main_last,
        comparison_last,
    ]
    if date is not None
)

# De datumwidget is een "conceptperiode". De grafieken gebruiken pas
# de toegepaste periode nadat de gebruiker expliciet op de knop klikt.
period_signature = (
    selected_street,
    comparison_street if compare else None,
    period_min,
    period_max,
)

if st.session_state.get("period_signature") != period_signature:
    st.session_state["period_signature"] = period_signature
    st.session_state["selected_period"] = (
        period_min,
        period_max,
    )
    st.session_state["applied_period"] = (
        period_min,
        period_max,
    )


def apply_selected_period():
    selected = st.session_state.get(
        "selected_period",
        (period_min, period_max),
    )
    if isinstance(selected, (tuple, list)) and len(selected) == 2:
        st.session_state["applied_period"] = tuple(selected)


def reset_selected_period():
    full_period = (
        period_min,
        period_max,
    )
    st.session_state["selected_period"] = full_period
    st.session_state["applied_period"] = full_period


st.sidebar.date_input(
    "Periode",
    min_value=period_min,
    max_value=period_max,
    key="selected_period",
)

apply_col, reset_col = st.sidebar.columns(2)

apply_col.button(
    "Periode toepassen",
    use_container_width=True,
    on_click=apply_selected_period,
)

reset_col.button(
    "Reset periode",
    use_container_width=True,
    on_click=reset_selected_period,
)

selected_dates = st.session_state.get(
    "applied_period",
    (period_min, period_max),
)

if (
    not isinstance(
        selected_dates,
        (tuple, list),
    )
    or len(selected_dates) != 2
):
    st.info(
        "Selecteer een begin- en einddatum."
    )
    st.stop()

start_date, end_date = selected_dates

flags = mode_flags(
    selected_modes
)


# ============================================================
# Frozen header
# ============================================================




# ============================================================
# Autosnelheid
# ============================================================

if analysis_type == "Autosnelheid":
    speed_views = [
        "Per uur",
        "Per dag",
        "Per week",
        "Per maand",
        "Per jaar",
        "24u-profiel",
        "Weekprofiel",
        "Jaarprofiel",
    ]

    # Dagelijkse histogrammen zijn compact en vormen de basis
    # voor dag/week/maand/jaar en de profielweergaven.
    with st.spinner(
        "Snelheidsgegevens verwerken..."
    ):
        speed_daily_main = (
            cached_get_daily_speed(
                main_id,
                start_date.isoformat(),
                end_date.isoformat(),
                start_hour,
                end_hour,
                min_uptime,
            )
        )

        speed_daily_compare = (
            cached_get_daily_speed(
                comparison_id,
                start_date.isoformat(),
                end_date.isoformat(),
                start_hour,
                end_hour,
                min_uptime,
            )
            if compare
            else pd.DataFrame()
        )

    speed_valid_main = valid_daily_speed(
        speed_daily_main,
        min_hours,
    )

    speed_avg_uptime = weighted_avg_uptime(
        speed_daily_main
    )

    speed_avg_uptime_text = (
        f"{speed_avg_uptime:.0%}"
        if speed_avg_uptime is not None
        else "—"
    )

    render_frozen_header(
        title="Autosnelheid",
        selected_street=selected_street,
        valid_days=len(speed_valid_main),
        avg_uptime_text=speed_avg_uptime_text,
        start_hour=start_hour,
        end_hour=end_hour,
        uptime_pct=uptime_pct,
        min_hours=min_hours,
        direction_choice=direction_choice,
        main_first=main_first,
        main_last=main_last,
        compare=compare,
        comparison_street=comparison_street,
        comparison_layout=comparison_layout,
    )

    speed_view = st.segmented_control(
        "Weergave",
        speed_views,
        default="Per dag",
        selection_mode="single",
        label_visibility="collapsed",
        key="speed_view",
    ) or "Per dag"

    speed_hourly_main = pd.DataFrame()
    speed_hourly_compare = pd.DataFrame()

    speed_hour_profile_main = pd.DataFrame()
    speed_hour_profile_compare = pd.DataFrame()

    # De zware uurdata worden alleen opgehaald wanneer
    # de gebruiker expliciet "Per uur" kiest.
    if speed_view == "Per uur":
        with st.spinner(
            "Uurlijkse snelheidsgegevens laden..."
        ):
            speed_hourly_main = (
                cached_get_hourly_speed(
                    main_id,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    start_hour,
                    end_hour,
                    min_uptime,
                )
            )

            if compare:
                speed_hourly_compare = (
                    cached_get_hourly_speed(
                        comparison_id,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        start_hour,
                        end_hour,
                        min_uptime,
                    )
                )

    if speed_view == "24u-profiel":
        with st.spinner(
            "24u-snelheidsprofiel berekenen..."
        ):
            speed_hour_profile_main = (
                cached_get_speed_hour_profile(
                    main_id,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    start_hour,
                    end_hour,
                    min_uptime,
                )
            )

            if compare:
                speed_hour_profile_compare = (
                    cached_get_speed_hour_profile(
                        comparison_id,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        start_hour,
                        end_hour,
                        min_uptime,
                    )
                )

    main_speed_plot = speed_view_data(
        speed_view,
        speed_hourly_main,
        speed_daily_main,
        speed_hour_profile_main,
        min_hours,
    )

    compare_speed_plot = (
        speed_view_data(
            speed_view,
            speed_hourly_compare,
            speed_daily_compare,
            speed_hour_profile_compare,
            min_hours,
        )
        if compare
        else pd.DataFrame()
    )

    overlay = (
        compare
        and comparison_layout
        == "Samen in één grafiek"
    )

    speed_rows = (
        2
        if compare and not overlay
        else 1
    )

    speed_fig = make_subplots(
        rows=speed_rows,
        cols=1,
        shared_xaxes=(
            compare
            and not overlay
            and speed_view in {
                "Per uur",
                "Per dag",
                "Per week",
                "Per maand",
                "Per jaar",
            }
        ),
        vertical_spacing=(
            .10
            if speed_rows == 2
            else 0
        ),
        subplot_titles=(
            [
                selected_street,
                comparison_street,
            ]
            if speed_rows == 2
            else None
        ),
    )

    main_speed_hover = speed_time_hover_data(
        speed_view,
        main_speed_plot,
    )

    compare_speed_hover = (
        speed_time_hover_data(
            speed_view,
            compare_speed_plot,
        )
        if compare
        else pd.DataFrame(
            columns=["x", "label"]
        )
    )

    if overlay and compare:
        combined_speed_hover = pd.concat(
            [
                main_speed_hover,
                compare_speed_hover,
            ],
            ignore_index=True,
        ).drop_duplicates(
            subset=["x"],
            keep="first",
        )

        add_time_hover_carrier(
            speed_fig,
            1,
            combined_speed_hover["x"],
            combined_speed_hover["label"],
        )
    else:
        add_time_hover_carrier(
            speed_fig,
            1,
            main_speed_hover["x"],
            main_speed_hover["label"],
        )

        if compare and speed_rows == 2:
            add_time_hover_carrier(
                speed_fig,
                2,
                compare_speed_hover["x"],
                compare_speed_hover["label"],
            )

    add_speed_traces(
        speed_fig,
        1,
        main_speed_plot,
        selected_street,
    )

    if compare:
        add_speed_traces(
            speed_fig,
            1 if overlay else 2,
            compare_speed_plot,
            comparison_street,
            True,
        )

    speed_x_title = {
        "Per uur": "Tijd (per uur)",
        "Per dag": "Tijd (per dag)",
        "Per week": "Tijd (per week)",
        "Per maand": "Tijd (per maand)",
        "Per jaar": "Tijd (per jaar)",
        "24u-profiel": "Uur in dag",
        "Weekprofiel": "Dag in week",
        "Jaarprofiel": "Maand in jaar",
    }[speed_view]

    speed_fig.update_xaxes(
        title_text=speed_x_title,
        unifiedhovertitle=dict(
            text="&#8203;",
        ),
    )

    if speed_view == "24u-profiel":
        speed_fig.update_xaxes(
            dtick=1,
        )

    elif speed_view == "Weekprofiel":
        speed_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=WEEKDAY_ABBR_NL,
        )

    elif speed_view == "Jaarprofiel":
        speed_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[
                MONTH_ABBR_NL[index]
                for index in range(1, 13)
            ],
        )

    speed_fig.update_yaxes(
        title_text=(
            "Autosnelheid (km/u)"
        ),
        gridcolor=GRID_COLOR,
        rangemode=(
            "tozero"
            if y_axis_from_zero
            else "normal"
        ),
    )

    speed_fig.update_layout(
        height=(
            720
            if speed_rows == 2
            else 520
        ),
        hovermode="x unified",
        margin=dict(
            t=(
                45
                if speed_rows == 2
                else 20
            ),
            l=20,
            r=30,
            b=20,
        ),
    )

    st.caption(
        "V50 = mediaansnelheid · "
        "V85 = snelheid waaronder 85% van de "
        "waarnemingen valt · "
        "V95 = 95e percentiel. "
        "Snelheid geldt alleen voor auto's en "
        "is niet per rijrichting beschikbaar."
    )

    st.plotly_chart(
        speed_fig,
        use_container_width=True,
    )

    st.divider()

    with st.expander(
        "ⓘ Hoe worden de snelheidsgegevens berekend?"
    ):
        st.markdown(
            f"""
De autosnelheid wordt afgeleid uit Telraams histogram met klassen van
**5 km/u**: 0–5, 5–10, …, 115–120 en **120+ km/u**.

Voor elke periode worden de histogrammen eerst gewogen met het aantal
auto's in het betreffende uur en daarna samengevoegd. Een druk uur telt
dus zwaarder mee dan een uur met weinig verkeer.

StraatVizier berekent vervolgens **V50, V85 en V95** door lineair binnen
de betreffende 5-km/u-klasse te interpoleren. De methode werd vergeleken
met Telraams eigen V85 en kwam vrijwel exact overeen.

Uren met minder dan **{uptime_pct}% uptime** worden uitgesloten.
Voor dag- en langere aggregaties moet een dag minstens **{min_hours}**
geldige uren hebben binnen **{start_hour:02d}:00–{end_hour:02d}:00**.

Snelheidsmetingen zijn indicatief. Telraam berekent snelheid alleen voor
objecten die als auto worden geclassificeerd; foutieve classificaties
kunnen daarom ook de snelheidsverdeling beïnvloeden.
            """
        )

    st.stop()


# ============================================================
# Dagelijkse aggregaten: altijd lichtgewicht
# ============================================================

daily_main_by_direction = {}
daily_compare_by_direction = {}

with st.spinner(
    "Verkeersgegevens verwerken..."
):
    for direction in directions:
        daily_main_by_direction[direction] = cached_get_daily(
            segment_id=main_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            start_hour=start_hour,
            end_hour=end_hour,
            min_uptime=min_uptime,
            direction=direction,
            **flags,
        )

if compare:
    with st.spinner(
        "Vergelijkingsgegevens verwerken..."
    ):
        for direction in directions:
            daily_compare_by_direction[direction] = cached_get_daily(
                segment_id=comparison_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                direction=direction,
                **flags,
            )

# Voor header en datakwaliteit gebruiken we bij een opgesplitste
# weergave de A→B-reeks; uptime/uren zijn identiek voor beide richtingen.
header_direction = directions[0]
daily_main = daily_main_by_direction[header_direction]
daily_compare = (
    daily_compare_by_direction[header_direction]
    if compare
    else None
)

valid_main_by_direction = {
    direction: valid_daily(data, min_hours)
    for direction, data in daily_main_by_direction.items()
}
valid_compare_by_direction = {
    direction: valid_daily(data, min_hours)
    for direction, data in daily_compare_by_direction.items()
}

valid_main = valid_main_by_direction[header_direction]
valid_compare = (
    valid_compare_by_direction[header_direction]
    if compare
    else None
)

avg_uptime_main = weighted_avg_uptime(
    daily_main
)

avg_uptime_text = (
    f"{avg_uptime_main:.0%}"
    if avg_uptime_main is not None
    else "—"
)

render_frozen_header(
    title=f"Aantallen {traffic_label.lower()}",
    selected_street=selected_street,
    valid_days=len(valid_main),
    avg_uptime_text=avg_uptime_text,
    start_hour=start_hour,
    end_hour=end_hour,
    uptime_pct=uptime_pct,
    min_hours=min_hours,
    direction_choice=direction_choice,
    main_first=main_first,
    main_last=main_last,
    compare=compare,
    comparison_street=comparison_street,
    comparison_layout=comparison_layout,
)


# ============================================================
# Weergave
# ============================================================

views = [
    "Per uur",
    "Per dag",
    "Per week",
    "Per maand",
    "Per jaar",
    "24u-profiel",
    "Weekprofiel",
    "Jaarprofiel",
]

view = st.segmented_control(
    "Weergave",
    views,
    default="Per dag",
    selection_mode="single",
    label_visibility="collapsed",
)

view = view or "Per dag"


# Rolling controls: compact
show_rolling = False
rolling_days = 31

if view == "Per dag":
    col_roll, col_window, col_space = st.columns(
        [2.4, 1.0, 4.6]
    )

    with col_roll:
        show_rolling = st.checkbox(
            "Toon voortschrijdend gemiddelde",
            value=True,
        )

    with col_window:
        rolling_days = st.selectbox(
            "Venster",
            [
                7,
                31,
                91,
            ],
            index=1,
            format_func=lambda value:
                f"{value} dagen",
            disabled=not show_rolling,
        )


# ============================================================
# Lazy loading zware weergaven
# ============================================================

hourly_main_by_direction = {}
hourly_compare_by_direction = {}
hour_profile_main_by_direction = {}
hour_profile_compare_by_direction = {}

if view == "Per uur":
    st.caption(
        "ⓘ Per uur gebruikt gedetailleerde "
        "uurgegevens. Bij een lange periode kan "
        "het laden iets langer duren."
    )

    with st.spinner("Uurgegevens laden..."):
        for direction in directions:
            hourly_main_by_direction[direction] = cached_get_hourly(
                segment_id=main_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                direction=direction,
                **flags,
            )

    if compare:
        with st.spinner("Uurgegevens vergelijkingsstraat laden..."):
            for direction in directions:
                hourly_compare_by_direction[direction] = cached_get_hourly(
                    segment_id=comparison_id,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    start_hour=start_hour,
                    end_hour=end_hour,
                    min_uptime=min_uptime,
                    direction=direction,
                    **flags,
                )


if view == "24u-profiel":
    with st.spinner("24u-profiel berekenen..."):
        for direction in directions:
            hour_profile_main_by_direction[direction] = cached_get_hour_profile(
                segment_id=main_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                direction=direction,
                **flags,
            )

    if compare:
        with st.spinner("24u-profiel vergelijkingsstraat berekenen..."):
            for direction in directions:
                hour_profile_compare_by_direction[direction] = cached_get_hour_profile(
                    segment_id=comparison_id,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    start_hour=start_hour,
                    end_hour=end_hour,
                    min_uptime=min_uptime,
                    direction=direction,
                    **flags,
                )


# ============================================================
# Plot
# ============================================================

comparison_overlay = (
    compare
    and comparison_layout == "Samen in één grafiek"
)

rows = (
    2
    if compare and not comparison_overlay
    else 1
)

fig = make_subplots(
    rows=rows,
    cols=1,
    specs=[
        [{"secondary_y": True}]
        for _ in range(rows)
    ],
    shared_xaxes=(
        compare
        and not comparison_overlay
        and view in {
            "Per uur",
            "Per dag",
            "Per week",
            "Per maand",
            "Per jaar",
        }
    ),
    vertical_spacing=(
        .10
        if compare and not comparison_overlay
        else 0
    ),
    subplot_titles=(
        [
            selected_street,
            comparison_street,
        ]
        if compare and not comparison_overlay
        else None
    ),
)

main_hover_direction = directions[0]

main_time_hover = traffic_time_hover_data(
    view,
    daily_main_by_direction[
        main_hover_direction
    ],
    valid_main_by_direction[
        main_hover_direction
    ],
    hourly=hourly_main_by_direction.get(
        main_hover_direction
    ),
    hour_profile=hour_profile_main_by_direction.get(
        main_hover_direction
    ),
    min_hours=min_hours,
)

compare_time_hover = (
    traffic_time_hover_data(
        view,
        daily_compare_by_direction[
            main_hover_direction
        ],
        valid_compare_by_direction[
            main_hover_direction
        ],
        hourly=hourly_compare_by_direction.get(
            main_hover_direction
        ),
        hour_profile=hour_profile_compare_by_direction.get(
            main_hover_direction
        ),
        min_hours=min_hours,
    )
    if compare
    else pd.DataFrame(
        columns=["x", "label"]
    )
)

if comparison_overlay and compare:
    combined_time_hover = pd.concat(
        [
            main_time_hover,
            compare_time_hover,
        ],
        ignore_index=True,
    ).drop_duplicates(
        subset=["x"],
        keep="first",
    )

    add_time_hover_carrier(
        fig,
        1,
        combined_time_hover["x"],
        combined_time_hover["label"],
    )
else:
    add_time_hover_carrier(
        fig,
        1,
        main_time_hover["x"],
        main_time_hover["label"],
    )

    if compare and rows == 2:
        add_time_hover_carrier(
            fig,
            2,
            compare_time_hover["x"],
            compare_time_hover["label"],
        )


y_label = None

for direction in directions:
    split = len(directions) > 1
    suffix = (
        direction_label(selected_street, direction)
        if split
        else (
            direction_label(selected_street, direction)
            if direction != "both"
            else None
        )
    )
    dash = "solid" if direction in {"both", "ab"} else "dash"

    current_label = add_view(
        fig=fig,
        row=1,
        view=view,
        street=selected_street,
        daily=daily_main_by_direction[direction],
        valid=valid_main_by_direction[direction],
        label=traffic_label,
        min_hours=min_hours,
        rolling_days=rolling_days,
        show_rolling=show_rolling,
        hourly=hourly_main_by_direction.get(direction),
        hour_profile=hour_profile_main_by_direction.get(direction),
        series_suffix=suffix,
        line_dash=dash,
    )

    y_label = y_label or current_label

if compare:
    for direction in directions:
        split = len(directions) > 1
        suffix = (
            direction_label(comparison_street, direction)
            if split
            else (
                direction_label(comparison_street, direction)
                if direction != "both"
                else None
            )
        )
        dash = "solid" if direction in {"both", "ab"} else "dash"

        add_view(
            fig=fig,
            row=(1 if comparison_overlay else 2),
            view=view,
            street=comparison_street,
            daily=daily_compare_by_direction[direction],
            valid=valid_compare_by_direction[direction],
            label=traffic_label,
            min_hours=min_hours,
            rolling_days=rolling_days,
            show_rolling=show_rolling,
            hourly=hourly_compare_by_direction.get(direction),
            hour_profile=hour_profile_compare_by_direction.get(direction),
            is_comparison=True,
            series_suffix=suffix,
            line_dash=dash,
        )


# Forceer de secundaire y-assen om zichtbaar te worden.
# Zonder een trace op secondary_y laat Plotly de rechter ticklabels soms weg.
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker=dict(opacity=0),
        showlegend=False,
        hoverinfo="skip",
    ),
    row=1,
    col=1,
    secondary_y=True,
)

if compare and not comparison_overlay:
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(opacity=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
        secondary_y=True,
    )


fig.update_yaxes(
    title_text=y_label,
    gridcolor=GRID_COLOR,
    gridwidth=1.15,
    tickfont=dict(
        size=13,
        color=AXIS_TEXT_COLOR,
        family="Arial",
    ),
    title_font=dict(
        size=14,
        color=AXIS_TEXT_COLOR,
        family="Arial",
    ),
    zeroline=True,
    zerolinecolor="#B8C2C9",
    zerolinewidth=1.2,
    rangemode=(
        "tozero"
        if y_axis_from_zero
        else "normal"
    ),
    row=1,
    col=1,
)

if compare and not comparison_overlay:
    fig.update_yaxes(
        title_text=y_label,
        gridcolor=GRID_COLOR,
        gridwidth=1.15,
        tickfont=dict(
            size=13,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        title_font=dict(
            size=14,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        zeroline=True,
        zerolinecolor="#B8C2C9",
        zerolinewidth=1.2,
        rangemode=(
            "tozero"
            if y_axis_from_zero
            else "normal"
        ),
        row=2,
        col=1,
    )


# Dezelfde y-schaal ook rechts tonen.
# Alleen de cijfers worden gespiegeld; de as-titel blijft links.
fig.update_yaxes(
    title_text=None,
    showgrid=False,
    zeroline=False,
    showticklabels=True,
    ticks="outside",
    tickfont=dict(
        size=13,
        color=AXIS_TEXT_COLOR,
        family="Arial",
    ),
    matches="y",
    row=1,
    col=1,
    secondary_y=True,
)

if compare and not comparison_overlay:
    fig.update_yaxes(
        title_text=None,
        showgrid=False,
        zeroline=False,
        showticklabels=True,
        ticks="outside",
        tickfont=dict(
            size=13,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        matches="y3",
        row=2,
        col=1,
        secondary_y=True,
    )


traffic_x_title = {
    "Per uur": "Tijd (per uur)",
    "Per dag": "Tijd (per dag)",
    "Per week": "Tijd (per week)",
    "Per maand": "Tijd (per maand)",
    "Per jaar": "Tijd (per jaar)",
    "24u-profiel": "Uur in dag",
    "Weekprofiel": "Dag in week",
    "Jaarprofiel": "Maand in jaar",
}[view]

fig.update_xaxes(
    title_text=traffic_x_title,
    unifiedhovertitle=dict(
        text="&#8203;",
    ),
    tickfont=dict(
        size=12,
        color=AXIS_TEXT_COLOR,
    ),
    gridcolor="#E7EBEE",
    gridwidth=.7,
)

# Bij vergelijking: toon tijdslabels ook op de bovenste gedeelde x-as.
if (
    compare
    and not comparison_overlay
    and view in {
        "Per uur",
        "Per dag",
        "Per week",
        "Per maand",
        "Per jaar",
    }
):
    fig.update_xaxes(
        showticklabels=True,
        row=1,
        col=1,
    )


for annotation in fig.layout.annotations:
    annotation.font = dict(
        size=17,
        color=SUBPLOT_TITLE_COLOR,
        family="Arial",
    )


fig.update_layout(
    height=(
        720
        if compare and not comparison_overlay
        else 500
    ),
    hovermode="x unified",
    legend_title=None,
    legend=dict(
        font=dict(
            size=12,
            color=AXIS_TEXT_COLOR,
        ),
        bgcolor="rgba(255,255,255,0.75)",
    ),
    margin=dict(
        t=(
            45
            if compare and not comparison_overlay
            else 20
        ),
        l=20,
        r=55,
        b=20,
    ),
)


st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# Datakwaliteit
# ============================================================

quality = monthly_average_daily_traffic(
    daily_main,
    min_hours_per_day=min_hours,
)

st.divider()

with st.expander(
    "ⓘ Hoe worden de verkeerscijfers berekend?"
):
    st.markdown(
        f"""
**Uptime en verkeerscijfers**

Telraam corrigeert de verkeerswaarde van elk meetuur al voor de
effectieve teltijd (*uptime*). StraatVizier voert daarom geen tweede
uptimecorrectie uit.

- Uren met minder dan **{uptime_pct}% uptime** worden met de huidige
  filters volledig uitgesloten.
- Een dag wordt alleen als geldige dag meegenomen wanneer minstens
  **{min_hours} geldige meeturen** beschikbaar zijn binnen
  **{start_hour:02d}:00–{end_hour:02d}:00**.
- Ontbrekende of uitgesloten uren en dagen worden niet aangevuld,
  geïnterpoleerd of naar een volledige periode geëxtrapoleerd.
- Week-, maand- en jaargemiddelden zijn gemiddelden over de geldige
  dagen in die periode.
- **Som over geldige dagen** is alleen de som van de beschikbare
  geldige dagwaarden. Bij ontbrekende dagen is dit dus geen volledig
  kalenderweek-, kalendermaand- of kalenderjaartotaal.

**Richtingen**

Voor segmentdata geldt bij Telraam steeds **A → B = left** en
**B → A = right**. StraatVizier gebruikt die vaste segmentoriëntatie
en toont daarnaast per straat een herkenbaar geografisch richtingslabel.

Bij straten met tramverkeer kan Telraam trams als **zwaar verkeer**
classificeren. Een richtingswaarde voor zwaar verkeer is daarom niet
automatisch uitsluitend vrachtverkeer.

De datakwaliteit hieronder helpt om de dekking van de gekozen periode
te beoordelen.
        """
    )

st.subheader(
    f"Datakwaliteit per maand — {selected_street}"
)

if quality.empty:
    st.info(
        "Geen maandgegevens beschikbaar "
        "voor de gekozen filters."
    )

else:
    quality_df = quality.copy()

    quality_df["month"] = (
        quality_df["month"]
        .dt.strftime("%Y-%m")
    )

    quality_df["avg_uptime"] = (
        quality_df["avg_uptime"]
        * 100
    ).round(1)

    quality_df["avg_daily_traffic"] = (
        quality_df["avg_daily_traffic"]
        .round(0)
        .astype(int)
    )

    quality_df = quality_df.rename(
        columns={
            "month": "Maand",
            "avg_daily_traffic":
                f"Gem. {traffic_label.lower()}/dag",
            "valid_days":
                "Geldige dagen",
            "avg_uptime":
                "Gem. uptime (%)",
        }
    )

    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True,
    )
