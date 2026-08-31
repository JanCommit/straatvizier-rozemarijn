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
APP_VERSION = "0.8.31"

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from straatvizier.analysis import (
    monthly_average_daily_traffic,
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
)


from straatvizier.ui.header import render_frozen_header

from straatvizier.ui.sidebar import render_global_filters

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
    page_title="StraatVizier",
    page_icon="🚦",
    layout="wide",
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
    traffic_label,
    direction_choice,
    directions,
    start_hour,
    end_hour,
    uptime_pct,
    min_uptime,
    min_hours,
    y_axis_from_zero,
) = render_global_filters(
    street_names,
    default_index,
)

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
# De tabel gebruikt dezelfde hoofdstraatdata en kwaliteitsdrempel als de grafiek,
# zodat de gebruiker de dekking van de getoonde periode kan beoordelen.
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
