import streamlit as st

from straatvizier.analysis import MODES
from straatvizier.segment_config import direction_label, sensor_history_label
from straatvizier.traffic_helpers import requested_directions, traffic_label_for


def render_global_filters(street_names, default_index):
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

    return (
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
    )
