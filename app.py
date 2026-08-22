from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

UI_PRIMARY = "#2E6F8E"
MAIN_STREET_COLOR = "#7FA6BC"
COMPARE_STREET_COLOR = "#A89CC8"
MAIN_TREND_COLOR = "#E8655B"
COMPARE_TREND_COLOR = "#6F5A8C"
GRID_COLOR = "#D1D8DE"
AXIS_TEXT_COLOR = "#3F4B55"
SUBPLOT_TITLE_COLOR = "#365F6B"
IVORY = "#F4F1E8"
SAGE = "#C7D0C2"

LOCAL_TIMEZONE = "Europe/Brussels"
APP_VERSION = "0.4.0"

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from straatvizier.analysis import (
    MODES,
    weekly_average_daily_traffic,
    monthly_average_daily_traffic,
    add_missing_days_as_gaps,
    add_rolling_average,
)

from straatvizier.database import (
    get_streets,
    get_measurement_bounds,
    get_daily_traffic,
    get_hourly_traffic,
    get_hour_profile,
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
        include_car=include_car,
        include_bike=include_bike,
        include_heavy=include_heavy,
        include_pedestrian=include_pedestrian,
    )


# ============================================================
# Helpers
# ============================================================

def traffic_label_for(labels):
    modes = [MODES[label] for label in labels]

    if set(modes) == {"car", "heavy"}:
        return "Gemotoriseerd verkeer"

    if len(labels) == 1:
        return labels[0]

    return " + ".join(labels)


def mode_flags(selected_modes):
    return {
        "include_car": "car" in selected_modes,
        "include_bike": "bike" in selected_modes,
        "include_heavy": "heavy" in selected_modes,
        "include_pedestrian": "pedestrian" in selected_modes,
    }


def valid_daily(daily_df, min_hours):
    if daily_df.empty:
        return daily_df.copy()

    return daily_df[
        daily_df["hours"] >= min_hours
    ].copy()


def weighted_avg_uptime(daily_df):
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

    return (
        result
        .set_index("week")
        .reindex(full_weeks)
        .rename_axis("week")
        .reset_index()
    )


def monthly_data(daily_df, min_hours):
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


def hourly_with_gaps(hourly_df):
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
                    name=street,
                    connectgaps=False,
                    line=dict(
                        color=street_color,
                        width=1.6,
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
                    name=f"{street} — dagelijks",
                    connectgaps=False,
                    line=dict(
                        color=street_color,
                        width=1.5,
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
                            f"{street} — "
                            f"{rolling_days}-daags gemiddelde"
                        ),
                        connectgaps=False,
                        line=dict(
                            color=trend_color,
                            width=3.2,
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
                    name=street,
                    connectgaps=False,
                    line=dict(
                        color=street_color,
                        width=2,
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
                    name=street,
                    connectgaps=False,
                    line=dict(
                        color=street_color,
                        width=2,
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
                    name=street,
                    line=dict(
                        color=street_color,
                        width=2.5,
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
                    name=street,
                    line=dict(
                        color=street_color,
                        width=2.5,
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
                ticktext=[
                    "Ma",
                    "Di",
                    "Wo",
                    "Do",
                    "Vr",
                    "Za",
                    "Zo",
                ],
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
                name=street,
                line=dict(
                    color=street_color,
                    width=2.5,
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
                "Jan",
                "Feb",
                "Mrt",
                "Apr",
                "Mei",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Okt",
                "Nov",
                "Dec",
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

if compare:
    comparison_street = st.sidebar.selectbox(
        "Tweede straat",
        [
            street
            for street in street_names
            if street != selected_street
        ],
    )

    st.sidebar.caption(
        "Filters gelden voor beide straten."
    )

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

selected_dates = st.sidebar.date_input(
    "Periode",
    value=(
        period_min,
        period_max,
    ),
    min_value=period_min,
    max_value=period_max,
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
# Dagelijkse aggregaten: altijd lichtgewicht
# ============================================================

with st.spinner(
    "Verkeersgegevens verwerken..."
):
    daily_main = cached_get_daily(
        segment_id=main_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        start_hour=start_hour,
        end_hour=end_hour,
        min_uptime=min_uptime,
        **flags,
    )

daily_compare = None

if compare:
    with st.spinner(
        "Vergelijkingsgegevens verwerken..."
    ):
        daily_compare = cached_get_daily(
            segment_id=comparison_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            start_hour=start_hour,
            end_hour=end_hour,
            min_uptime=min_uptime,
            **flags,
        )


valid_main = valid_daily(
    daily_main,
    min_hours,
)

valid_compare = (
    valid_daily(
        daily_compare,
        min_hours,
    )
    if compare
    else None
)


# ============================================================
# Frozen header
# ============================================================

avg_uptime_main = weighted_avg_uptime(
    daily_main
)

avg_uptime_text = (
    f"{avg_uptime_main:.0%}"
    if avg_uptime_main is not None
    else "—"
)

comparison_note = (
    f" · vergelijking met {comparison_street}"
    if compare
    else ""
)

st.html(
    f"""
    <style>
        .sv-head {{
            position: fixed;
            top: 3.6rem;
            left: 22rem;
            right: 1.25rem;
            z-index: 9999;
            background: #2B2F33;
            border: 1px solid #3A4046;
            border-radius: 12px;
            padding: .78rem 1rem .82rem;
            box-shadow:
                0 8px 22px rgba(0,0,0,.14);
        }}

        .sv-title {{
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.2;
            color: {IVORY};
            margin-bottom: .18rem;
        }}

        .sv-context {{
            font-size: .86rem;
            color: {SAGE};
            margin-bottom: .62rem;
        }}

        .sv-metrics {{
            display: grid;
            grid-template-columns:
                repeat(4, minmax(0,1fr));
            gap: .9rem;
        }}

        .sv-label {{
            font-size: .75rem;
            color: {SAGE};
            margin-bottom: .08rem;
        }}

        .sv-value {{
            font-size: 1.08rem;
            font-weight: 650;
            color: {IVORY};
        }}

        .sv-spacer {{
            height: 1.4rem;
        }}

        @media(max-width:900px) {{
            .sv-head {{
                left: 1rem;
                right: 1rem;
                top: 3.4rem;
            }}

            .sv-metrics {{
                grid-template-columns:
                    repeat(2,1fr);
            }}

            .sv-spacer {{
                height: 5.5rem;
            }}
        }}
    </style>

    <div class="sv-head">
        <div class="sv-title">
            {traffic_label} — {selected_street}
        </div>

        <div class="sv-context">
            Lokale Belgische tijd
            {start_hour:02d}:00–{end_hour:02d}:00
            · minimum uptime {uptime_pct}%
            · minimum {min_hours} geldige uren per dag
            {comparison_note}
        </div>

        <div class="sv-metrics">
            <div>
                <div class="sv-label">
                    Eerste meting
                </div>
                <div class="sv-value">
                    {main_first.strftime("%d/%m/%Y")}
                </div>
            </div>

            <div>
                <div class="sv-label">
                    Laatste meting
                </div>
                <div class="sv-value">
                    {main_last.strftime("%d/%m/%Y")}
                </div>
            </div>

            <div>
                <div class="sv-label">
                    Geldige dagen
                </div>
                <div class="sv-value">
                    {len(valid_main)}
                </div>
            </div>

            <div>
                <div class="sv-label">
                    Gem. uptime
                </div>
                <div class="sv-value">
                    {avg_uptime_text}
                </div>
            </div>
        </div>
    </div>

    <div class="sv-spacer"></div>
    """
)


# ============================================================
# Weergave
# ============================================================

st.header(
    "Verkeersverloop"
)

views = [
    "Per uur",
    "Per dag",
    "Per week",
    "Per maand",
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
rolling_days = 30

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
                30,
                90,
            ],
            index=1,
            format_func=lambda value:
                f"{value} dagen",
            disabled=not show_rolling,
        )


# ============================================================
# Lazy loading zware weergaven
# ============================================================

hourly_main = None
hourly_compare = None

hour_profile_main = None
hour_profile_compare = None

if view == "Per uur":
    st.caption(
        "ⓘ Per uur gebruikt gedetailleerde "
        "uurgegevens. Bij een lange periode kan "
        "het laden iets langer duren."
    )

    with st.spinner(
        "Uurgegevens laden..."
    ):
        hourly_main = cached_get_hourly(
            segment_id=main_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            start_hour=start_hour,
            end_hour=end_hour,
            min_uptime=min_uptime,
            **flags,
        )

    if compare:
        with st.spinner(
            "Uurgegevens vergelijkingsstraat laden..."
        ):
            hourly_compare = cached_get_hourly(
                segment_id=comparison_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                **flags,
            )


if view == "24u-profiel":
    with st.spinner(
        "24u-profiel berekenen..."
    ):
        hour_profile_main = (
            cached_get_hour_profile(
                segment_id=main_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                **flags,
            )
        )

    if compare:
        with st.spinner(
            "24u-profiel vergelijkingsstraat berekenen..."
        ):
            hour_profile_compare = (
                cached_get_hour_profile(
                    segment_id=comparison_id,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    start_hour=start_hour,
                    end_hour=end_hour,
                    min_uptime=min_uptime,
                    **flags,
                )
            )


# ============================================================
# Plot
# ============================================================

rows = (
    2
    if compare
    else 1
)

fig = make_subplots(
    rows=rows,
    cols=1,
    shared_xaxes=(
        compare
        and view in {
            "Per uur",
            "Per dag",
            "Per week",
            "Per maand",
        }
    ),
    vertical_spacing=(
        .10
        if compare
        else 0
    ),
    subplot_titles=(
        [
            selected_street,
            comparison_street,
        ]
        if compare
        else None
    ),
)

y_label = add_view(
    fig=fig,
    row=1,
    view=view,
    street=selected_street,
    daily=daily_main,
    valid=valid_main,
    label=traffic_label,
    min_hours=min_hours,
    rolling_days=rolling_days,
    show_rolling=show_rolling,
    hourly=hourly_main,
    hour_profile=hour_profile_main,
)

if compare:
    add_view(
        fig=fig,
        row=2,
        view=view,
        street=comparison_street,
        daily=daily_compare,
        valid=valid_compare,
        label=traffic_label,
        min_hours=min_hours,
        rolling_days=rolling_days,
        show_rolling=show_rolling,
        hourly=hourly_compare,
        hour_profile=hour_profile_compare,
        is_comparison=True,
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

if compare:
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


fig.update_xaxes(
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
    and view in {
        "Per uur",
        "Per dag",
        "Per week",
        "Per maand",
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
        if compare
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
            if compare
            else 20
        ),
        l=20,
        r=20,
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
