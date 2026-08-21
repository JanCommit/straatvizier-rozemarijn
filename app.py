from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

UI_PRIMARY = "#2E6F8E"

RAW_COLOR = "#8FB3CC"
TREND_COLOR = "#174F6B"

MODE_COLORS = {
    "pedestrian": "#E98763",
    "bike": "#2F8F68",
    "car": "#4A9BB8",
    "heavy": "#165F8F",
    "night": "#6F7377",
}

# ============================================================
# Python pad configureren
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ============================================================
# Imports uit StraatVizier
# ============================================================

from straatvizier.analysis import (
    MODES,
    prepare_measurements,
    filter_measurements,
    add_combined_mode,
    daily_selected_traffic,
    weekly_average_daily_traffic,
    monthly_average_daily_traffic,
    add_missing_days_as_gaps,
    add_rolling_average,
)

from straatvizier.database import (
    get_measurements,
    get_streets,
)


# ============================================================
# Streamlit configuratie
# ============================================================

st.set_page_config(
    page_title="StraatVizier",
    page_icon="🚦",
    layout="wide",
)


st.title("StraatVizier")
st.caption(
    "Historische verkeersanalyse op basis van Telraam-data"
)


# ============================================================
# Cache
# ============================================================

@st.cache_data(ttl=300)
def cached_get_streets():
    return get_streets()


@st.cache_data(ttl=300)
def cached_get_measurements(segment_id: int):
    return get_measurements(segment_id=segment_id)


# ============================================================
# Straten
# ============================================================

streets_df = cached_get_streets()

if streets_df.empty:
    st.error("Geen straten gevonden in Supabase.")
    st.stop()

street_options = (
    streets_df
    .sort_values("street")
    .reset_index(drop=True)
)


# ============================================================
# Sidebar
# ============================================================

st.sidebar.header("Filters")

selected_street = st.sidebar.selectbox(
    "Straat",
    options=street_options["street"].tolist(),
)

street_row = (
    street_options[
        street_options["street"] == selected_street
    ]
    .iloc[0]
)

segment_id = int(street_row["segment_id"])


selected_mode_labels = st.sidebar.multiselect(
    "Vervoersmiddelen",
    options=list(MODES.keys()),
    default=["Auto's", "Zwaar verkeer"],
)

if not selected_mode_labels:
    st.warning("Selecteer minstens één vervoersmiddel.")
    st.stop()

selected_modes = [
    MODES[label]
    for label in selected_mode_labels
]


if set(selected_modes) == {"car", "heavy"}:
    traffic_label = "Gemotoriseerd verkeer"
elif len(selected_mode_labels) == 1:
    traffic_label = selected_mode_labels[0]
else:
    traffic_label = " + ".join(selected_mode_labels)


start_hour, end_hour = st.sidebar.slider(
    "Uren",
    min_value=0,
    max_value=24,
    value=(8, 18),
    step=1,
)

min_uptime_percent = st.sidebar.slider(
    "Minimum uptime per uur",
    min_value=0,
    max_value=100,
    value=50,
    step=5,
)

min_uptime = min_uptime_percent / 100


max_valid_hours = max(
    1,
    end_hour - start_hour,
)

min_hours_per_day = st.sidebar.slider(
    "Minimum geldige uren per dag",
    min_value=1,
    max_value=max_valid_hours,
    value=min(8, max_valid_hours),
)


# ============================================================
# Data ophalen
# ============================================================

with st.spinner("Verkeersdata laden..."):
    raw_df = cached_get_measurements(
        segment_id=segment_id,
    )

if raw_df.empty:
    st.warning(
        "Voor deze straat zijn geen metingen gevonden."
    )
    st.stop()


prepared_df = prepare_measurements(raw_df)


# ============================================================
# Beschikbare periode
# ============================================================

first_date = (
    prepared_df["measured_at_local"]
    .min()
    .date()
)

last_date = (
    prepared_df["measured_at_local"]
    .max()
    .date()
)

selected_dates = st.sidebar.date_input(
    "Periode",
    value=(first_date, last_date),
    min_value=first_date,
    max_value=last_date,
)

if not isinstance(selected_dates, (tuple, list)):
    st.info("Selecteer een begin- en einddatum.")
    st.stop()

if len(selected_dates) != 2:
    st.info("Selecteer een begin- en einddatum.")
    st.stop()

start_date, end_date = selected_dates


selected_df = prepared_df[
    (
        prepared_df["measured_at_local"].dt.date
        >= start_date
    )
    &
    (
        prepared_df["measured_at_local"].dt.date
        <= end_date
    )
].copy()


# ============================================================
# Filteren
# ============================================================

filtered_df = filter_measurements(
    selected_df,
    start_hour=start_hour,
    end_hour=end_hour,
    min_uptime=min_uptime,
)

filtered_df = add_combined_mode(
    filtered_df,
    selected_modes,
)

daily_df = daily_selected_traffic(
    filtered_df,
)

valid_daily_df = daily_df[
    daily_df["hours"] >= min_hours_per_day
].copy()


# ============================================================
# KPI's
# ============================================================

st.subheader(
    f"{traffic_label} — {selected_street}"
)

st.caption(
    f"Lokale tijd {start_hour:02d}:00–"
    f"{end_hour:02d}:00 · "
    f"minimum uptime {min_uptime_percent}% · "
    f"minimum {min_hours_per_day} geldige uren per dag"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Eerste meting",
    first_date.strftime("%d/%m/%Y"),
)

col2.metric(
    "Laatste meting",
    last_date.strftime("%d/%m/%Y"),
)

col3.metric(
    "Geldige dagen",
    len(valid_daily_df),
)

if not filtered_df.empty:
    col4.metric(
        "Gem. uptime",
        f"{filtered_df['uptime'].mean():.0%}",
    )
else:
    col4.metric(
        "Gem. uptime",
        "—",
    )


# ============================================================
# KORTE TERMIJN
# ============================================================

st.divider()

st.header("Periode in detail")

(
    detail_tab_daily,
    detail_tab_weekly,
    detail_tab_monthly,
    detail_tab_hourly,
    detail_tab_day_profile,
    detail_tab_week_profile,
    detail_tab_month_profile,
) = st.tabs(
    [
        "Per dag",
        "Per week",
        "Per maand",
        "Per uur",
        "24u-profiel",
        "Weekprofiel",
        "Maandprofiel",
    ]
)

# ------------------------------------------------------------
# Per dag
# ------------------------------------------------------------

with detail_tab_daily:
    if valid_daily_df.empty:
        st.info("Geen geldige dagen voor deze selectie.")
    else:
        daily_plot_df = add_missing_days_as_gaps(valid_daily_df)

        daily_fig = px.line(
            daily_plot_df,
            x="date",
            y="value",
            labels={
                "date": "Datum",
                "value": traffic_label,
            },
        )

        daily_fig.update_traces(
            connectgaps=False,
            line=dict(
                color=RAW_COLOR,
                width=1.6,
            ),
            hovertemplate=(
                "%{x|%d/%m/%Y}<br>"
                f"{traffic_label}: "
                "%{y:,.0f}<extra></extra>"
            ),
        )

        daily_fig.update_layout(
            xaxis_title=None,
            yaxis_title=f"{traffic_label} per dag",
            hovermode="x unified",
        )

        st.plotly_chart(
            daily_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# Per week
# ------------------------------------------------------------

with detail_tab_weekly:
    weekly_df = weekly_average_daily_traffic(
        daily_df,
        min_hours_per_day=min_hours_per_day,
    )

    if weekly_df.empty:
        st.info("Geen weekgegevens voor deze selectie.")
    else:
        weekly_plot_df = weekly_df.copy()
        weekly_plot_df["week"] = pd.to_datetime(
            weekly_plot_df["week"]
        )

        full_weeks = pd.date_range(
            weekly_plot_df["week"].min(),
            weekly_plot_df["week"].max(),
            freq="W-MON",
        )

        weekly_plot_df = (
            weekly_plot_df
            .set_index("week")
            .reindex(full_weeks)
            .rename_axis("week")
            .reset_index()
        )

        weekly_fig = px.line(
            weekly_plot_df,
            x="week",
            y="avg_daily_traffic",
            markers=True,
            labels={
                "week": "Week",
                "avg_daily_traffic":
                    f"Gemiddeld {traffic_label.lower()} per dag",
            },
        )

        weekly_fig.update_traces(
            connectgaps=False,
            line=dict(
                color=UI_PRIMARY,
                width=2,
            ),
            marker=dict(
                color=UI_PRIMARY,
                size=5,
            ),
        )

        weekly_fig.update_layout(
            xaxis_title=None,
            yaxis_title=(
                f"Gemiddeld {traffic_label.lower()} "
                f"per geldige dag"
            ),
            hovermode="x unified",
        )

        st.plotly_chart(
            weekly_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# Per maand
# ------------------------------------------------------------

with detail_tab_monthly:
    monthly_df = monthly_average_daily_traffic(
        daily_df,
        min_hours_per_day=min_hours_per_day,
    )

    if monthly_df.empty:
        st.info("Geen maandgegevens voor deze selectie.")
    else:
        monthly_plot_df = monthly_df.copy()
        monthly_plot_df["month"] = pd.to_datetime(
            monthly_plot_df["month"]
        )

        full_months = pd.date_range(
            monthly_plot_df["month"].min(),
            monthly_plot_df["month"].max(),
            freq="MS",
        )

        monthly_plot_df = (
            monthly_plot_df
            .set_index("month")
            .reindex(full_months)
            .rename_axis("month")
            .reset_index()
        )

        monthly_fig = px.line(
            monthly_plot_df,
            x="month",
            y="avg_daily_traffic",
            markers=True,
            labels={
                "month": "Maand",
                "avg_daily_traffic":
                    f"Gemiddeld {traffic_label.lower()} per dag",
            },
        )

        monthly_fig.update_traces(
            connectgaps=False,
            line=dict(
                color=UI_PRIMARY,
                width=2,
            ),
            marker=dict(
                color=UI_PRIMARY,
                size=6,
            ),
        )

        monthly_fig.update_layout(
            xaxis_title=None,
            yaxis_title=(
                f"Gemiddeld {traffic_label.lower()} "
                f"per geldige dag"
            ),
            hovermode="x unified",
        )

        st.plotly_chart(
            monthly_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# Per uur
# ------------------------------------------------------------

with detail_tab_hourly:
    if filtered_df.empty:
        st.info("Geen uurmetingen voor deze selectie.")
    else:
        hourly_fig = px.line(
            filtered_df,
            x="measured_at_local",
            y="selected_traffic",
            labels={
                "measured_at_local": "Tijd",
                "selected_traffic": traffic_label,
            },
        )

        hourly_fig.update_traces(
            connectgaps=False,
            line=dict(
                color=RAW_COLOR,
                width=1.2,
            ),
        )

        hourly_fig.update_layout(
            xaxis_title=None,
            yaxis_title=traffic_label,
            hovermode="x unified",
        )

        st.plotly_chart(
            hourly_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# 24u-profiel
# ------------------------------------------------------------

with detail_tab_day_profile:
    if filtered_df.empty:
        st.info("Geen uurmetingen voor deze selectie.")
    else:
        profile_df = (
            filtered_df
            .groupby("hour", as_index=False)
            .agg(
                avg_traffic=("selected_traffic", "mean")
            )
        )

        profile_fig = px.line(
            profile_df,
            x="hour",
            y="avg_traffic",
            markers=True,
            labels={
                "hour": "Uur van de dag",
                "avg_traffic":
                    f"Gemiddeld {traffic_label.lower()}",
            },
        )

        profile_fig.update_traces(
            line=dict(
                color=UI_PRIMARY,
                width=2.5,
            ),
            marker=dict(
                color=UI_PRIMARY,
                size=7,
            ),
        )

        profile_fig.update_xaxes(
            dtick=1,
            tickmode="linear",
        )

        profile_fig.update_layout(
            xaxis_title="Uur",
            yaxis_title=(
                f"Gemiddeld {traffic_label.lower()}"
            ),
        )

        st.plotly_chart(
            profile_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# Weekprofiel
# ------------------------------------------------------------

with detail_tab_week_profile:
    if valid_daily_df.empty:
        st.info(
            "Geen geldige daggegevens voor deze selectie."
        )
    else:
        week_profile_df = valid_daily_df.copy()
        week_profile_df["weekday"] = (
            week_profile_df["date"].dt.weekday
        )

        week_profile_df = (
            week_profile_df
            .groupby("weekday", as_index=False)
            .agg(
                avg_traffic=("value", "mean"),
                valid_days=("date", "count"),
            )
        )

        weekday_names = {
            0: "Ma",
            1: "Di",
            2: "Wo",
            3: "Do",
            4: "Vr",
            5: "Za",
            6: "Zo",
        }

        week_profile_df["weekday_name"] = (
            week_profile_df["weekday"]
            .map(weekday_names)
        )

        week_profile_fig = px.line(
            week_profile_df,
            x="weekday",
            y="avg_traffic",
            markers=True,
            custom_data=[
                "weekday_name",
                "valid_days",
            ],
        )

        week_profile_fig.update_traces(
            line=dict(
                color=UI_PRIMARY,
                width=2.5,
            ),
            marker=dict(
                color=UI_PRIMARY,
                size=8,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                f"Gemiddeld {traffic_label.lower()}: "
                "%{y:,.0f}/dag<br>"
                "Geldige dagen: %{customdata[1]}"
                "<extra></extra>"
            ),
        )

        week_profile_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=[
                "Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"
            ],
        )

        week_profile_fig.update_layout(
            xaxis_title=None,
            yaxis_title=(
                f"Gemiddeld {traffic_label.lower()} per dag"
            ),
        )

        st.plotly_chart(
            week_profile_fig,
            use_container_width=True,
        )

# ------------------------------------------------------------
# Maandprofiel
# ------------------------------------------------------------

with detail_tab_month_profile:
    if valid_daily_df.empty:
        st.info(
            "Geen geldige daggegevens voor deze selectie."
        )
    else:
        month_profile_df = valid_daily_df.copy()
        month_profile_df["month_number"] = (
            month_profile_df["date"].dt.month
        )

        month_profile_df = (
            month_profile_df
            .groupby("month_number", as_index=False)
            .agg(
                avg_traffic=("value", "mean"),
                valid_days=("date", "count"),
            )
        )

        month_names = {
            1: "Jan",
            2: "Feb",
            3: "Mrt",
            4: "Apr",
            5: "Mei",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Okt",
            11: "Nov",
            12: "Dec",
        }

        month_profile_df["month"] = (
            month_profile_df["month_number"]
            .map(month_names)
        )

        month_profile_fig = px.line(
            month_profile_df,
            x="month_number",
            y="avg_traffic",
            markers=True,
            custom_data=[
                "month",
                "valid_days",
            ],
        )

        month_profile_fig.update_traces(
            line=dict(
                color=UI_PRIMARY,
                width=2.5,
            ),
            marker=dict(
                color=UI_PRIMARY,
                size=8,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                f"Gemiddeld {traffic_label.lower()}: "
                "%{y:,.0f}/dag<br>"
                "Geldige dagen: %{customdata[1]}"
                "<extra></extra>"
            ),
        )

        month_profile_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[
                "Jan", "Feb", "Mrt", "Apr", "Mei", "Jun",
                "Jul", "Aug", "Sep", "Okt", "Nov", "Dec",
            ],
        )

        month_profile_fig.update_layout(
            xaxis_title=None,
            yaxis_title=(
                f"Gemiddeld {traffic_label.lower()} per dag"
            ),
            hovermode="x unified",
        )

        st.plotly_chart(
            month_profile_fig,
            use_container_width=True,
        )

# ============================================================
# LANGE TERMIJN
# ============================================================

st.divider()

st.header("Lange-termijnevolutie")

rolling_days = st.selectbox(
    "Voortschrijdend gemiddelde",
    options=[
        7,
        30,
        90,
    ],
    index=1,
    format_func=lambda value:
        f"{value} dagen",
)

show_raw = st.checkbox(
    "Toon dagelijkse waarden",
    value=True,
)

show_rolling = st.checkbox(
    "Toon voortschrijdend gemiddelde",
    value=True,
)


if valid_daily_df.empty:
    st.info(
        "Geen geldige data voor lange-termijnanalyse."
    )

else:
    trend_df = add_missing_days_as_gaps(
        valid_daily_df
    )

    trend_df = add_rolling_average(
        trend_df,
        window_days=rolling_days,
    )

    trend_fig = go.Figure()

    if show_raw:
        trend_fig.add_trace(
            go.Scatter(
                x=trend_df["date"],
                y=trend_df["value"],
                mode="lines",
                name="Dagelijkse waarde",
                connectgaps=False,
                line=dict(
                    color=RAW_COLOR,
                    width=1.2,
                ),
                opacity=0.50,
            )
        )

    if show_rolling:
        trend_fig.add_trace(
            go.Scatter(
                x=trend_df["date"],
                y=trend_df["rolling_average"],
                mode="lines",
                name=f"{rolling_days}-daags gemiddelde",
                connectgaps=False,
                line=dict(
                    color=TREND_COLOR,
                    width=3,
                ),
            )
        )

    trend_fig.update_layout(
        xaxis_title=None,
        yaxis_title=traffic_label,
        hovermode="x unified",
        legend_title=None,
    )

    st.plotly_chart(
        trend_fig,
        use_container_width=True,
    )


# ============================================================
# Datakwaliteit
# ============================================================

monthly_df = monthly_average_daily_traffic(
    daily_df,
    min_hours_per_day=min_hours_per_day,
)

st.divider()

st.subheader("Datakwaliteit per maand")

if monthly_df.empty:
    st.info(
        "Geen maandgegevens beschikbaar "
        "voor de gekozen filters."
    )

else:
    quality_df = monthly_df.copy()

    quality_df["month"] = (
        quality_df["month"]
        .dt.strftime("%Y-%m")
    )

    quality_df["avg_uptime"] = (
        quality_df["avg_uptime"] * 100
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
            "valid_days": "Geldige dagen",
            "avg_uptime": "Gem. uptime (%)",
        }
    )

    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True,
    )