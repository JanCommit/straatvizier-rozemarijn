"""Definieer de globale Streamlit-filters en vertaal ze naar applicatiekeuzes."""

import streamlit as st

from straatvizier.analysis import MODES
from straatvizier.segment_config import (
    direction_label,
    sensor_history_label,
    night_counts_start_date,
)
from straatvizier.traffic_helpers import requested_directions, traffic_label_for


def render_global_filters(street_names, default_index):
    """Render alle globale filters en geef de genormaliseerde keuzes aan app.py terug."""
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

    analysis_type = st.sidebar.radio(
        "Analyse",
        ["Verkeersaantallen", "Autosnelheid"],
        index=0,
    )

    main_night_start = (
        night_counts_start_date(selected_street)
        if analysis_type == "Verkeersaantallen"
        else None
    )

    traffic_context = "Verkeer bij daglicht"

    if analysis_type == "Verkeersaantallen":
        traffic_context_options = [
            "Verkeer bij daglicht",
        ]

        if main_night_start is not None:
            traffic_context_options.append(
                "Verkeer zonder daglicht (S2)"
            )

        traffic_context = st.sidebar.radio(
            "Meetcontext",
            traffic_context_options,
            index=0,
            help=(
                "Kies daglichtverkeer met classificatie naar "
                "vervoersmiddel, of ongeclassificeerde S2-detecties "
                "bij onvoldoende daglicht. Beide meetcontexten worden "
                "niet gecombineerd."
            ),
        )

    comparison_street = None
    comparison_layout = "Onder elkaar"

    if compare:
        comparison_candidates = [
            street
            for street in street_names
            if street != selected_street
        ]

        if (
            analysis_type == "Verkeersaantallen"
            and traffic_context == "Verkeer zonder daglicht (S2)"
        ):
            comparison_candidates = [
                street
                for street in comparison_candidates
                if night_counts_start_date(street) is not None
            ]

        if not comparison_candidates:
            st.sidebar.warning(
                "Er is geen andere straat met bruikbare "
                "S2-nachtdata beschikbaar."
            )
            st.stop()

        comparison_street = st.sidebar.selectbox(
            "Tweede straat",
            comparison_candidates,
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

    if analysis_type == "Verkeersaantallen":
        comparison_night_start = (
            night_counts_start_date(
                comparison_street
            )
            if compare
            else None
        )

        if traffic_context == "Verkeer bij daglicht":
            mode_labels = st.sidebar.multiselect(
                "Verkeer bij daglicht",
                list(MODES.keys()),
                default=[
                    "Auto's",
                    "Zwaar verkeer",
                ],
                help=(
                    "Bij voldoende daglicht kan Telraam verkeer "
                    "classificeren naar vervoersmiddel."
                ),
            )

            if not mode_labels:
                st.warning(
                    "Selecteer minstens één vervoersmiddel "
                    "voor verkeer bij daglicht."
                )
                st.stop()

            selected_modes = [
                MODES[label]
                for label in mode_labels
            ]
            include_night = False
            traffic_label = traffic_label_for(
                mode_labels
            )

        else:
            mode_labels = []
            selected_modes = []
            include_night = True
            traffic_label = "Verkeer zonder daglicht (S2)"

            st.sidebar.caption(
                "S2-detecties bij onvoldoende daglicht worden "
                "niet naar vervoersmiddel geclassificeerd."
            )

            if main_night_start is not None:
                st.sidebar.caption(
                    f"Nachtdata {selected_street}: vanaf "
                    f"{main_night_start.strftime('%d/%m/%Y')}"
                )

            if (
                compare
                and comparison_night_start is not None
            ):
                st.sidebar.caption(
                    f"Nachtdata {comparison_street}: vanaf "
                    f"{comparison_night_start.strftime('%d/%m/%Y')}"
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
        include_night = False
        traffic_label = "Autosnelheid"
        direction_choice = "Beide richtingen"
        directions = ["both"]

        st.sidebar.caption(
            "Snelheid is alleen beschikbaar voor auto's "
            "en niet per rijrichting."
        )

    if (
        analysis_type == "Verkeersaantallen"
        and include_night
    ):
        default_hours = (0, 4)
    else:
        default_hours = (9, 16)

    start_hour, end_hour = st.sidebar.slider(
        "Uren",
        min_value=0,
        max_value=24,
        value=default_hours,
        step=1,
        help=(
            "Standaard wordt voor verkeer bij daglicht 09:00–16:00 "
            "gebruikt en voor verkeer zonder daglicht 00:00–04:00. "
            "Andere uren kiezen wordt op aanvraag opnieuw berekend."
        ),
    )

    if (start_hour, end_hour) != default_hours:
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

    show_data_quality = st.sidebar.checkbox(
        "Toon datakwaliteitstabel",
        value=False,
        help=(
            "Toon onder de grafiek de datadekking "
            "voor de gekozen weergave."
        ),
    )

    return (
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
    )
