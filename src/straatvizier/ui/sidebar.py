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

    def section_title(label):
        st.sidebar.markdown(
            f"""
            <div style="
                margin-top: 1.25rem;
                margin-bottom: 0.58rem;
                padding-bottom: 0.32rem;
                border-bottom: 1px solid rgba(40, 122, 139, 0.22);
                color: #287A8B;
                font-size: 0.78rem;
                font-weight: 750;
                letter-spacing: 0.065em;
            ">
                {label}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # LOGO
    # ========================================================
    st.sidebar.image(
        "assets/watpasseert-logo.png",
        use_container_width=True,
    )

    # ========================================================
    # STRAATSELECTIE
    # ========================================================
    section_title("STRAATSELECTIE")

    selected_street = st.sidebar.selectbox(
        "Straat",
        street_names,
        index=default_index,
        key="selected_street",
    )

    compare = st.sidebar.checkbox(
        "Vergelijk met tweede straat",
        value=False,
        key="compare_streets",
    )

    # Gebruik de huidige Streamlit-state om de vergelijkingslijst al bovenaan
    # correct te kunnen beperken wanneer nachtmodus actief is.
    previous_analysis = st.session_state.get(
        "analysis_type",
        "Verkeersaantallen",
    )
    previous_context = st.session_state.get(
        "traffic_context",
        "Verkeer bij daglicht (S1 en S2)",
    )
    night_comparison_active = (
        previous_analysis == "Verkeersaantallen"
        and previous_context == "Verkeer zonder daglicht (enkel S2)"
    )

    comparison_street = None
    comparison_layout = "Onder elkaar"

    if compare:
        comparison_candidates = [
            street
            for street in street_names
            if street != selected_street
        ]

        if night_comparison_active:
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

        current_comparison = st.session_state.get(
            "comparison_street"
        )
        if current_comparison not in comparison_candidates:
            st.session_state["comparison_street"] = (
                comparison_candidates[0]
            )

        comparison_street = st.sidebar.selectbox(
            "Tweede straat",
            comparison_candidates,
            key="comparison_street",
        )

        comparison_layout = st.sidebar.radio(
            "Vergelijkingsweergave",
            [
                "Onder elkaar",
                "Samen in één grafiek",
            ],
            index=0,
            key="comparison_layout",
            help=(
                "Onder elkaar toont elke straat apart. "
                "Samen in één grafiek maakt absolute verschillen "
                "tussen beide straten direct zichtbaar."
            ),
        )

    # ========================================================
    # TYPE METING
    # ========================================================
    section_title("TYPE METING")

    analysis_type = st.sidebar.radio(
        "Type meting",
        ["Verkeersaantallen", "Autosnelheid"],
        index=0,
        key="analysis_type",
        label_visibility="collapsed",
    )

    main_night_start = (
        night_counts_start_date(selected_street)
        if analysis_type == "Verkeersaantallen"
        else None
    )

    # ========================================================
    # LICHTCONDITIE
    # ========================================================
    traffic_context = "Verkeer bij daglicht (S1 en S2)"

    if analysis_type == "Verkeersaantallen":
        section_title("LICHTCONDITIE")

        traffic_context_options = [
            "Verkeer bij daglicht (S1 en S2)",
        ]

        if main_night_start is not None:
            traffic_context_options.append(
                "Verkeer zonder daglicht (enkel S2)"
            )

        current_context = st.session_state.get("traffic_context")
        if current_context not in traffic_context_options:
            st.session_state["traffic_context"] = traffic_context_options[0]

        traffic_context = st.sidebar.radio(
            "Lichtconditie",
            traffic_context_options,
            index=0,
            key="traffic_context",
            label_visibility="collapsed",
            help=(
                "Bij daglicht kan Telraam verkeer classificeren "
                "naar vervoersmiddel. Zonder daglicht gebruikt S2 "
                "ongeclassificeerde detecties."
            ),
        )

        # Als de gebruiker net naar nachtmodus schakelt en de reeds gekozen
        # tweede straat geen nachtdata heeft, herstart Streamlit één keer met
        # een geldige kandidaat. Daardoor blijft de widget visueel bovenaan.
        if compare and traffic_context == "Verkeer zonder daglicht (enkel S2)":
            valid_night_candidates = [
                street
                for street in street_names
                if street != selected_street
                and night_counts_start_date(street) is not None
            ]
            if not valid_night_candidates:
                st.sidebar.warning(
                    "Er is geen andere straat met bruikbare "
                    "S2-nachtdata beschikbaar."
                )
                st.stop()
            if comparison_street not in valid_night_candidates:
                st.session_state["comparison_street"] = valid_night_candidates[0]
                st.rerun()

    # ========================================================
    # ANALYSE-INHOUD
    # ========================================================
    if analysis_type == "Verkeersaantallen":
        comparison_night_start = (
            night_counts_start_date(comparison_street)
            if compare
            else None
        )

        if traffic_context == "Verkeer bij daglicht (S1 en S2)":
            mode_labels = st.sidebar.multiselect(
                "Vervoersmiddelen",
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
            traffic_label = traffic_label_for(mode_labels)

        else:
            mode_labels = []
            selected_modes = []
            include_night = True
            traffic_label = "Verkeer zonder daglicht (S2)"

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
                "B → A met *_right."
            ),
        )

        directions = requested_directions(direction_choice)

        if direction_choice in {"A → B", "B → A"}:
            code = "ab" if direction_choice == "A → B" else "ba"
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

    # ========================================================
    # FILTERS
    # ========================================================
    section_title("FILTERS")

    active_view = st.session_state.get("traffic_view", "Per dag")
    min_hours_disabled = (
        analysis_type == "Verkeersaantallen"
        and active_view in {"Per uur", "Per dag", "24u-profiel"}
    )

    default_hours = (
        (0, 4)
        if analysis_type == "Verkeersaantallen" and include_night
        else (9, 16)
    )

    start_hour, end_hour = st.sidebar.slider(
        "Geselecteerde uren",
        min_value=0,
        max_value=24,
        value=default_hours,
        step=1,
        help=(
            "Voor verkeer bij daglicht wordt standaard 09:00–16:00 "
            "gebruikt, omdat deze uren gedurende het hele jaar bij daglicht "
            "vallen. Voor verkeer zonder daglicht wordt standaard 00:00–04:00 "
            "gebruikt, omdat deze uren gedurende het hele jaar in het donker "
            "vallen. Andere uren kunnen vrij worden gekozen; de gegevens "
            "worden dan opnieuw server-side berekend."
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
            "Telraam corrigeert de verkeerswaarde al voor de effectieve "
            "teltijd. Deze grens bepaalt welke uren als kwalitatief geldig "
            "tellen. In Per uur en Per dag blijven beschikbare gecorrigeerde "
            "waarden zichtbaar; in het 24u-profiel worden alleen uren boven "
            "deze grens gemiddeld."
        ),
    )
    min_uptime = uptime_pct / 100

    max_hours = max(1, end_hour - start_hour)

    min_hours = st.sidebar.slider(
        "Minimum geldige uren per dag",
        min_value=1,
        max_value=max_hours,
        value=min(8, max_hours),
        disabled=min_hours_disabled,
        help=(
            "Bepaalt voor week-, maand- en jaargemiddelden en voor week- "
            "en jaarprofielen of een dag voldoende geldige uren heeft. "
            "Niet van toepassing op Per uur, Per dag en 24u-profiel."
        ),
    )

    if min_hours_disabled:
        st.sidebar.caption(
            "ⓘ Minimum geldige uren per dag is niet van toepassing "
            "op deze weergave."
        )

    # Wordt later in app.py gevuld zodra de beschikbare meetperiode bekend is.
    period_container = st.sidebar.container()

    # ========================================================
    # WEERGAVE
    # ========================================================
    section_title("WEERGAVE")

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

    # ========================================================
    # DATA & SENSOREN
    # ========================================================
    with st.sidebar.expander("DATA & SENSOREN", expanded=False):
        main_sensor_history = sensor_history_label(selected_street)
        if main_sensor_history:
            st.markdown(
                f"Sensor {selected_street}: {main_sensor_history}"
            )

        if compare:
            comparison_sensor_history = sensor_history_label(
                comparison_street
            )
            if comparison_sensor_history:
                st.markdown(
                    f"Sensor {comparison_street}: "
                    f"{comparison_sensor_history}"
                )

        if main_night_start is not None:
            st.markdown(
                f"Nachtdata {selected_street}: vanaf "
                f"{main_night_start.strftime('%d/%m/%Y')}"
            )

        if compare:
            comparison_night_start_info = night_counts_start_date(
                comparison_street
            )
            if comparison_night_start_info is not None:
                st.markdown(
                    f"Nachtdata {comparison_street}: vanaf "
                    f"{comparison_night_start_info.strftime('%d/%m/%Y')}"
                )

        st.markdown(
            "S2-detecties bij onvoldoende daglicht worden "
            "niet naar vervoersmiddel geclassificeerd."
        )

    # ========================================================
    # OVER WAT PASSEERT?
    # ========================================================
    with st.sidebar.expander("OVER WAT PASSEERT?", expanded=False):
        st.markdown(
            """
**WatPasseert?** maakt het mogelijk om lokale verkeersmetingen over
een langere periode te bekijken en te vergelijken. De standaardweergave
van Telraam toont gegevens binnen een beperkter tijdsvenster; dit
dashboard bewaart en ontsluit de volledige beschikbare tijdsreeks.

De verkeersgegevens zijn afkomstig van **Telraam** en worden via de
Telraam-API opgehaald en lokaal bewaard. De dataset wordt elke nacht
automatisch aangevuld met de recentste beschikbare metingen.

WatPasseert? is een onafhankelijk dashboard en is niet ontwikkeld door
of verbonden aan Telraam. De resultaten blijven afhankelijk van de
mogelijkheden en beperkingen van de gebruikte Telraam-sensoren.
            """
        )

    # ========================================================
    # CONTACT / FEEDBACK
    # ========================================================
    feedback_submission = None

    with st.sidebar.expander("CONTACT / FEEDBACK", expanded=False):
        st.markdown(
            "Heb je een vraag, opmerking of suggestie? "
            "Stuur hier een bericht."
        )

        with st.form(
            "feedback_form",
            clear_on_submit=True,
        ):
            feedback_email = st.text_input(
                "E-mailadres (optioneel)",
                max_chars=254,
                placeholder="naam@voorbeeld.be",
            )

            feedback_message = st.text_area(
                "Bericht",
                max_chars=1000,
                height=120,
                placeholder="Typ hier je bericht...",
            )

            st.caption(
                "E-mailadres is optioneel. "
                "Wil je graag een antwoord ontvangen? "
                "Vul dan je e-mailadres in."
            )

            feedback_sent = st.form_submit_button(
                "Bericht versturen",
                use_container_width=True,
            )

        if feedback_sent:
            message = feedback_message.strip()
            email = feedback_email.strip()

            if len(message) < 5:
                st.error(
                    "Schrijf een bericht van minstens 5 tekens."
                )
            elif email and (
                "@" not in email
                or email.startswith("@")
                or email.endswith("@")
            ):
                st.error(
                    "Vul een geldig e-mailadres in "
                    "of laat het veld leeg."
                )
            else:
                feedback_submission = {
                    "message": message,
                    "email": email or None,
                }

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
        period_container,
        feedback_submission,
    )

