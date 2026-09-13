"""StraatVizier Streamlit-applicatie.

Dit bestand orkestreert de dashboardflow: globale filters, beschikbare
meetperiode, gerichte data-ophaling, kwaliteitsfilters en de keuze tussen
verkeersintensiteit en autosnelheid. Berekeningen en Plotly-details zitten
zoveel mogelijk in gespecialiseerde modules onder ``src/straatvizier``.
"""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


LOCAL_TIMEZONE = "Europe/Brussels"
APP_VERSION = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from straatvizier.analysis import (
    weekly_average_daily_traffic,
    monthly_average_daily_traffic,
    yearly_average_daily_traffic,
)

from straatvizier.database import (
    get_streets,
    get_measurement_bounds,
    get_daily_traffic,
    get_hourly_traffic,
    get_hour_profile,
    get_hourly_speed,
    get_daily_speed,
    get_speed_hour_profile,
    submit_feedback,
)


from straatvizier.ui.header import render_frozen_header

from straatvizier.ui.sidebar import render_global_filters

from straatvizier.segment_config import night_counts_start_date

from straatvizier.data_helpers import (
    valid_daily,
    weighted_avg_uptime,
)

from straatvizier.traffic_helpers import (
    mode_flags,
)

from straatvizier.period_state import (
    initialize_period_state,
    apply_period_state,
    reset_period_state,
)



from straatvizier.ui.traffic_figure import (
    build_traffic_figure,
)


from straatvizier.speed_helpers import (
    speed_view_data,
)

from straatvizier.ui.speed_chart import (
    valid_daily_speed,
)

from straatvizier.ui.speed_figure import (
    build_speed_figure,
)


st.set_page_config(
    page_title="WatPasseert?",
    page_icon="assets/watpasseert-icon.png",
    layout="wide",
)

st.markdown(
    """
    <style>
        :root {
            --wp-petrol: #287A8B;
            --wp-anthracite: #30383D;
            --wp-page: #F7F8F7;
            --wp-surface: #FFFFFF;
            --wp-border: rgba(48, 56, 61, 0.12);
        }

        .stApp {
            background: var(--wp-page);
        }

        [data-testid="stAppViewContainer"] {
            background: var(--wp-page);
        }

        [data-testid="stHeader"] {
            background: rgba(247, 248, 247, 0.94);
        }

        [data-testid="stSidebar"] {
            background: #F2F5F4;
            border-right: 1px solid var(--wp-border);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a {
            color: var(--wp-petrol);
        }

        [data-testid="stSidebar"] input:focus,
        [data-testid="stSidebar"] textarea:focus {
            border-color: var(--wp-petrol) !important;
            box-shadow: 0 0 0 1px var(--wp-petrol) !important;
        }

        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--wp-petrol) !important;
            box-shadow: 0 0 0 1px rgba(40, 122, 139, 0.20) !important;
        }

        [data-baseweb="checkbox"] [aria-checked="true"],
        [data-baseweb="radio"] [aria-checked="true"] {
            accent-color: var(--wp-petrol);
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: var(--wp-petrol);
            border-color: var(--wp-petrol);
        }

        [data-testid="stMetric"],
        [data-testid="stDataFrame"] {
            background: var(--wp-surface);
        }

        hr {
            border-color: var(--wp-border);
        }

        /* Weergave-tabs / segmented controls */
        [data-testid="stSegmentedControl"] button {
            background: rgba(255, 255, 255, 0.88);
            color: var(--wp-anthracite);
            border-color: rgba(48, 56, 61, 0.14);
            border-radius: 6px;
            font-weight: 500;
            transition:
                background-color 120ms ease,
                border-color 120ms ease,
                color 120ms ease;
        }

        [data-testid="stSegmentedControl"] button:hover {
            background: rgba(40, 122, 139, 0.07);
            border-color: rgba(40, 122, 139, 0.28);
            color: #236D7C;
        }

        [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: rgba(40, 122, 139, 0.13);
            border-color: rgba(40, 122, 139, 0.42);
            color: #236D7C;
            font-weight: 650;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Gecachete database-oproepen
# Streamlit voert het script bij widgetinteractie opnieuw uit. Deze wrappers
# voorkomen identieke Supabase-oproepen gedurende maximaal 24 uur.
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
    include_night: bool = False,
    night_start_date: str | None = None,
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
        include_night=include_night,
        night_start_date=night_start_date,
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
    include_night: bool = False,
    night_start_date: str | None = None,
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
        include_night=include_night,
        night_start_date=night_start_date,
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
    include_night: bool = False,
    night_start_date: str | None = None,
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
        include_night=include_night,
        night_start_date=night_start_date,
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




# ============================================================
# Straten en globale filters
# De sidebar vertaalt gebruikerskeuzes naar genormaliseerde waarden die de
# rest van app.py gebruikt voor data-ophaling en visualisatie.
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

(
    selected_street,
    compare,
    comparison_street,
    comparison_layout,
    analysis_type,
    mode_labels,
    selected_modes,
    include_night,
    traffic_label,
    direction_choice,
    directions,
    start_hour,
    end_hour,
    uptime_pct,
    min_uptime,
    min_hours,
    y_axis_from_zero,
    show_data_quality,
    period_container,
    feedback_submission,
) = render_global_filters(
    street_names,
    default_index,
)

if feedback_submission is not None:
    try:
        submit_feedback(
            message=feedback_submission["message"],
            email=feedback_submission["email"],
            street=selected_street,
        )
    except (ValueError, RuntimeError):
        st.sidebar.error(
            "Het bericht kon niet worden verstuurd. "
            "Controleer de invoer en probeer opnieuw."
        )
    except Exception:
        st.sidebar.error(
            "Het bericht kon tijdelijk niet worden verstuurd. "
            "Probeer later opnieuw."
        )
    else:
        st.sidebar.success("Bedankt. Je bericht is verstuurd.")

# ============================================================
# Segmenten en beschikbare periodes
# Bij vergelijking wordt de volledige beschikbare kalender-range van beide
# straten gebruikt; elke straat kan binnen die range eigen meetgaten hebben.
# ============================================================

main_row = streets[
    streets["street"] == selected_street
].iloc[0]

main_id = int(
    main_row["segment_id"]
)

main_night_start = night_counts_start_date(
    selected_street
)

main_first_utc, main_last_utc = cached_get_bounds(
    main_id
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
comparison_night_start = None

if compare:
    comparison_row = streets[
        streets["street"]
        == comparison_street
    ].iloc[0]

    comparison_id = int(
        comparison_row["segment_id"]
    )

    comparison_night_start = night_counts_start_date(
        comparison_street
    )

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


# In S2-night mode, the usable measurement period starts only when
# reliable night counts are available for the selected street.
main_effective_first = (
    max(main_first, main_night_start)
    if include_night and main_night_start is not None
    else main_first
)

comparison_effective_first = (
    max(comparison_first, comparison_night_start)
    if (
        include_night
        and comparison_first is not None
        and comparison_night_start is not None
    )
    else comparison_first
)


period_min = min(
    date
    for date in [
        main_effective_first,
        comparison_effective_first,
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
initialize_period_state(
    selected_street=selected_street,
    comparison_street=comparison_street,
    compare=compare,
    period_min=period_min,
    period_max=period_max,
)


def apply_selected_period():
    apply_period_state(
        period_min,
        period_max,
    )


def reset_selected_period():
    reset_period_state(
        period_min,
        period_max,
    )


with period_container:
    st.date_input(
        "Periode",
        min_value=period_min,
        max_value=period_max,
        key="selected_period",
    )

    apply_col, reset_col = st.columns(2)

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

main_query_start = (
    max(start_date, main_effective_first)
    if include_night
    else start_date
)

comparison_query_start = (
    max(start_date, comparison_effective_first)
    if (
        include_night
        and comparison_effective_first is not None
    )
    else start_date
)

flags = mode_flags(
    selected_modes
)
flags["include_night"] = include_night

st.sidebar.divider()
st.sidebar.caption(f"WatPasseert? v{APP_VERSION}")

# ============================================================
# Autosnelheid
# Deze tak stopt na het renderen van de snelheidsanalyse. Daardoor wordt de
# verkeersdata verderop niet onnodig opgehaald wanneer snelheid gekozen is.
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

    speed_fig = build_speed_figure(
        speed_view=speed_view,
        main_speed_plot=main_speed_plot,
        compare_speed_plot=compare_speed_plot,
        selected_street=selected_street,
        comparison_street=comparison_street,
        compare=compare,
        comparison_layout=comparison_layout,
        y_axis_from_zero=y_axis_from_zero,
        overlay=overlay,
        speed_rows=speed_rows,
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
# Dagdata vormt de basis voor de meeste verkeersweergaven en datakwaliteit.
# Uurdata wordt verderop alleen geladen voor views die ze werkelijk nodig hebben.
# ============================================================

daily_main_by_direction = {}
daily_compare_by_direction = {}

for direction in directions:
    daily_main_by_direction[direction] = cached_get_daily(
        segment_id=main_id,
        start_date=main_query_start.isoformat(),
        end_date=end_date.isoformat(),
        start_hour=start_hour,
        end_hour=end_hour,
        min_uptime=min_uptime,
        direction=direction,
        night_start_date=(
            main_night_start.isoformat()
            if main_night_start is not None
            else None
        ),
        **flags,
    )

if compare:
    for direction in directions:
        daily_compare_by_direction[direction] = cached_get_daily(
            segment_id=comparison_id,
            start_date=comparison_query_start.isoformat(),
            end_date=end_date.isoformat(),
            start_hour=start_hour,
            end_hour=end_hour,
            min_uptime=min_uptime,
            direction=direction,
            night_start_date=(
                comparison_night_start.isoformat()
                if comparison_night_start is not None
                else None
            ),
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
    main_first=main_effective_first,
    main_last=main_last,
    compare=compare,
    comparison_street=comparison_street,
    comparison_layout=comparison_layout,
)


# ============================================================
# Weergave
# De view bepaalt zowel de grafiekvorm als welke aanvullende datasets lazy
# geladen moeten worden. Het voortschrijdend gemiddelde bestaat alleen per dag.
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
    key="traffic_view",
)

view = view or "Per dag"


# Rolling controls: compact
show_rolling = False
rolling_days = 31

if view == "Per dag":
    col_roll, col_label, col_window, col_space = st.columns(
        [1.55, 0.35, 0.85, 5.25],
        gap="small",
        vertical_alignment="center",
    )

    with col_roll:
        show_rolling = st.checkbox(
            "Toon voortschrijdend gemiddelde",
            value=True,
        )

    with col_label:
        st.markdown("Venster")

    with col_window:
        rolling_days = st.selectbox(
            "Venster",
            [7, 31, 91],
            index=1,
            format_func=lambda value: f"{value} dagen",
            disabled=not show_rolling,
            label_visibility="collapsed",
        )

# ============================================================
# Lazy loading zware weergaven
# Gedetailleerde uurdata en 24u-profielen worden pas opgehaald wanneer de
# gekozen view ze nodig heeft; dit houdt gewone dashboard-reruns lichter.
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
                start_date=main_query_start.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                direction=direction,
                night_start_date=(
                    main_night_start.isoformat()
                    if main_night_start is not None
                    else None
                ),
                **flags,
            )

    if compare:
        with st.spinner("Uurgegevens vergelijkingsstraat laden..."):
            for direction in directions:
                hourly_compare_by_direction[direction] = cached_get_hourly(
                    segment_id=comparison_id,
                    start_date=comparison_query_start.isoformat(),
                    end_date=end_date.isoformat(),
                    start_hour=start_hour,
                    end_hour=end_hour,
                    min_uptime=min_uptime,
                    direction=direction,
                    night_start_date=(
                        comparison_night_start.isoformat()
                        if comparison_night_start is not None
                        else None
                    ),
                    **flags,
                )


if view == "24u-profiel":
    with st.spinner("24u-profiel berekenen..."):
        for direction in directions:
            hour_profile_main_by_direction[direction] = cached_get_hour_profile(
                segment_id=main_id,
                start_date=main_query_start.isoformat(),
                end_date=end_date.isoformat(),
                start_hour=start_hour,
                end_hour=end_hour,
                min_uptime=min_uptime,
                direction=direction,
                night_start_date=(
                    main_night_start.isoformat()
                    if main_night_start is not None
                    else None
                ),
                **flags,
            )

    if compare:
        with st.spinner("24u-profiel vergelijkingsstraat berekenen..."):
            for direction in directions:
                hour_profile_compare_by_direction[direction] = cached_get_hour_profile(
                    segment_id=comparison_id,
                    start_date=comparison_query_start.isoformat(),
                    end_date=end_date.isoformat(),
                    start_hour=start_hour,
                    end_hour=end_hour,
                    min_uptime=min_uptime,
                    direction=direction,
                    night_start_date=(
                        comparison_night_start.isoformat()
                        if comparison_night_start is not None
                        else None
                    ),
                    **flags,
                )


# ============================================================
# Plot
# Vanaf hier is alle benodigde verkeersdata voorbereid. De gespecialiseerde
# figure-module bepaalt traces, hovergedrag, assen en vergelijkingslayout.
# ============================================================

fig = build_traffic_figure(
    view=view,
    selected_street=selected_street,
    comparison_street=comparison_street,
    compare=compare,
    comparison_layout=comparison_layout,
    directions=directions,
    daily_main_by_direction=daily_main_by_direction,
    daily_compare_by_direction=daily_compare_by_direction,
    valid_main_by_direction=valid_main_by_direction,
    valid_compare_by_direction=valid_compare_by_direction,
    hourly_main_by_direction=hourly_main_by_direction,
    hourly_compare_by_direction=hourly_compare_by_direction,
    hour_profile_main_by_direction=hour_profile_main_by_direction,
    hour_profile_compare_by_direction=hour_profile_compare_by_direction,
    traffic_label=traffic_label,
    min_hours=min_hours,
    rolling_days=rolling_days,
    show_rolling=show_rolling,
    y_axis_from_zero=y_axis_from_zero,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# Datakwaliteit
# Optioneel: toon de datadekking in dezelfde tijdsindeling als de actieve view.
# ============================================================

st.divider()

with st.expander(
    "ⓘ\u2002Hoe worden de verkeerscijfers berekend?"
):
    st.markdown(
        f"""
**Uptime en verkeerscijfers**

Telraam corrigeert de verkeerswaarde van elk meetuur al voor de
effectieve teltijd (*uptime*). WatPasseert? voert daarom geen tweede
uptimecorrectie uit. Een lagere uptime betekent wel dat een uurwaarde
op minder effectieve meettijd is gebaseerd en daardoor onzekerder kan zijn.

- In **Per uur** worden alle beschikbare, door Telraam gecorrigeerde
  uurwaarden getoond, ook onder **{uptime_pct}% uptime**.
- In **Per dag** worden alle beschikbare gecorrigeerde uurwaarden binnen
  **{start_hour:02d}:00–{end_hour:02d}:00** samengevoegd. Een beschikbaar
  uur met lage uptime wordt dus niet uit het dagtotaal verwijderd.
- Voor **Per week, Per maand en Per jaar** bepaalt de minimum uptime welke
  uren als geldig tellen. Een dag wordt alleen in het gemiddelde opgenomen
  wanneer minstens **{min_hours} geldige uren** beschikbaar zijn.
- Week-, maand- en jaargemiddelden worden uitsluitend berekend over de
  geldige dagen. Ontbrekende of ongeldige dagen worden niet als nul gerekend.

**Profielen**

- Het **24u-profiel** berekent per uur van de dag het gemiddelde over
  metingen met minstens **{uptime_pct}% uptime** binnen de geselecteerde periode.
- Het **weekprofiel** berekent per weekdag het gemiddelde over de geldige
  dagen van dat type binnen de geselecteerde periode.
- Het **jaarprofiel** berekent per kalendermaand het gemiddelde dagelijkse
  verkeer over alle geldige dagen van die maand binnen de geselecteerde periode.

**Datakwaliteit**

**Minimum geldige uren per dag** is niet van toepassing op **Per uur**,
**Per dag** en **24u-profiel** en wordt daar in de sidebar uitgeschakeld.
Ontbrekende metingen worden niet geïnterpoleerd en ontbrekende dagen
worden niet als nul behandeld.

**Richtingen**

Voor segmentdata geldt bij Telraam steeds **A → B = left** en
**B → A = right**. WatPasseert? gebruikt die vaste segmentoriëntatie.

Bij straten met tramverkeer kan Telraam trams als **zwaar verkeer**
classificeren. Een richtingswaarde voor zwaar verkeer is daarom niet
automatisch uitsluitend vrachtverkeer.

Schakel **Toon datakwaliteitstabel** in de sidebar in om de dekking
van de gekozen periode te bekijken.
        """
    )

if show_data_quality:
    valid_quality = daily_main[
        daily_main["hours"] >= min_hours
    ].copy()

    if view in {"Per uur", "Per dag", "24u-profiel"}:
        quality_label = "dag"
        quality = daily_main.copy()
        if not quality.empty:
            quality = quality.rename(
                columns={
                    "date": "period",
                    "value": "avg_daily_traffic",
                    "hours": "valid_hours",
                }
            )
            quality["valid_days"] = 1

    elif view == "Per week":
        quality_label = "week"
        quality = weekly_average_daily_traffic(
            daily_main,
            min_hours_per_day=min_hours,
        )
        if not quality.empty:
            quality = quality.rename(columns={"week": "period"})

    elif view in {"Per maand", "Jaarprofiel"}:
        quality_label = "maand"
        quality = monthly_average_daily_traffic(
            daily_main,
            min_hours_per_day=min_hours,
        )
        if not quality.empty:
            quality = quality.rename(columns={"month": "period"})

    elif view == "Per jaar":
        quality_label = "jaar"
        quality = yearly_average_daily_traffic(
            daily_main,
            min_hours_per_day=min_hours,
        )
        if not quality.empty:
            quality = quality.rename(columns={"year": "period"})

    else:  # Weekprofiel
        quality_label = "weekdag"
        quality = valid_quality.copy()
        if not quality.empty:
            quality["period"] = quality["date"].dt.dayofweek
            quality = (
                quality
                .groupby("period", as_index=False)
                .agg(
                    avg_daily_traffic=("value", "mean"),
                    valid_days=("date", "count"),
                    avg_uptime=("avg_uptime", "mean"),
                )
            )

    st.subheader(
        f"Datakwaliteit per {quality_label} — {selected_street}"
    )

    if quality.empty:
        st.info(
            "Geen datakwaliteitsgegevens beschikbaar "
            "voor de gekozen filters."
        )
    else:
        quality_df = quality.copy()

        if quality_label == "dag":
            quality_df["period"] = pd.to_datetime(
                quality_df["period"]
            ).dt.strftime("%d/%m/%Y")
            quality_df = quality_df[
                [
                    "period",
                    "valid_hours",
                    "avg_uptime",
                ]
            ]
            rename_columns = {
                "period": "Dag",
                "valid_hours": "Geldige uren",
                "avg_uptime": "Gem. uptime (%)",
            }

        elif quality_label == "week":
            week_start = pd.to_datetime(quality_df["period"])
            week_end = week_start + pd.Timedelta(days=6)
            quality_df["period"] = (
                week_start.dt.strftime("%d/%m/%Y")
                + " – "
                + week_end.dt.strftime("%d/%m/%Y")
            )
            quality_df = quality_df[
                [
                    "period",
                    "valid_days",
                    "avg_uptime",
                ]
            ]
            rename_columns = {
                "period": "Week",
                "valid_days": "Geldige dagen",
                "avg_uptime": "Gem. uptime (%)",
            }

        elif quality_label == "maand":
            quality_df["period"] = pd.to_datetime(
                quality_df["period"]
            ).dt.strftime("%Y-%m")
            quality_df = quality_df[
                [
                    "period",
                    "valid_days",
                    "avg_uptime",
                ]
            ]
            rename_columns = {
                "period": "Maand",
                "valid_days": "Geldige dagen",
                "avg_uptime": "Gem. uptime (%)",
            }

        elif quality_label == "jaar":
            quality_df["period"] = pd.to_datetime(
                quality_df["period"]
            ).dt.strftime("%Y")
            quality_df = quality_df[
                [
                    "period",
                    "valid_days",
                    "avg_uptime",
                ]
            ]
            rename_columns = {
                "period": "Jaar",
                "valid_days": "Geldige dagen",
                "avg_uptime": "Gem. uptime (%)",
            }

        else:
            weekday_names = [
                "Maandag",
                "Dinsdag",
                "Woensdag",
                "Donderdag",
                "Vrijdag",
                "Zaterdag",
                "Zondag",
            ]
            quality_df["period"] = quality_df["period"].map(
                dict(enumerate(weekday_names))
            )
            quality_df = quality_df[
                [
                    "period",
                    "valid_days",
                    "avg_uptime",
                ]
            ]
            rename_columns = {
                "period": "Weekdag",
                "valid_days": "Geldige dagen",
                "avg_uptime": "Gem. uptime (%)",
            }

        quality_df["avg_uptime"] = (
            quality_df["avg_uptime"] * 100
        ).round(1)

        quality_df = quality_df.rename(
            columns=rename_columns
        )

        st.dataframe(
            quality_df,
            use_container_width=True,
            hide_index=True,
        )
