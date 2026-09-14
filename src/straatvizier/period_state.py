"""Beheer van geselecteerde en toegepaste perioden in Streamlit session state."""

import streamlit as st


DEFAULT_PERIOD_MODE = "max"


def initialize_period_state(
    selected_street,
    comparison_street,
    compare,
    period_min,
    period_max,
):
    """Initialiseer en synchroniseer de periode met de actieve periodemodus.

    In de standaardmodus ``max`` volgt de periode automatisch de volledige
    beschikbare meetperiode van de geselecteerde straat of straten.

    In modus ``specific`` blijven een eerder geselecteerde en toegepaste
    periode behouden wanneer de straatcontext of databounds wijzigen.
    """
    period_mode = st.session_state.setdefault(
        "period_mode",
        DEFAULT_PERIOD_MODE,
    )

    period_signature = (
        selected_street,
        comparison_street if compare else None,
        period_min,
        period_max,
    )

    signature_changed = (
        st.session_state.get("period_signature")
        != period_signature
    )

    if signature_changed:
        st.session_state["period_signature"] = period_signature

        if period_mode == "max":
            full_period = (
                period_min,
                period_max,
            )
            st.session_state["selected_period"] = full_period
            st.session_state["applied_period"] = full_period

    # Zorg ook bij een nieuwe sessie voor geldige beginwaarden.
    if "selected_period" not in st.session_state:
        st.session_state["selected_period"] = (
            period_min,
            period_max,
        )

    if "applied_period" not in st.session_state:
        st.session_state["applied_period"] = tuple(
            st.session_state["selected_period"]
        )


def apply_period_state(
    period_min,
    period_max,
):
    """Kopieer de huidige selectie naar de periode die de grafiek gebruikt."""
    selected = st.session_state.get(
        "selected_period",
        (period_min, period_max),
    )

    if (
        isinstance(selected, (tuple, list))
        and len(selected) == 2
    ):
        st.session_state["applied_period"] = tuple(selected)


def reset_period_state(
    period_min,
    period_max,
):
    """Schakel terug naar maximale periode en herstel het volledige bereik."""
    full_period = (
        period_min,
        period_max,
    )

    st.session_state["period_mode"] = DEFAULT_PERIOD_MODE
    st.session_state["selected_period"] = full_period
    st.session_state["applied_period"] = full_period
