"""Beheer van geselecteerde en toegepaste perioden in Streamlit session state."""

import streamlit as st


def initialize_period_state(
    selected_street,
    comparison_street,
    compare,
    period_min,
    period_max,
):
    """Initialiseer de periode opnieuw wanneer straat of beschikbare grenzen wijzigen."""
    # Reset alleen wanneer de straatcontext of beschikbare databounds wijzigen.
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


def apply_period_state(
    period_min,
    period_max,
):
    """Kopieer de huidige selectie naar de periode die de grafiek werkelijk gebruikt."""
    selected = st.session_state.get(
        "selected_period",
        (period_min, period_max),
    )
    if isinstance(selected, (tuple, list)) and len(selected) == 2:
        st.session_state["applied_period"] = tuple(selected)


def reset_period_state(
    period_min,
    period_max,
):
    """Herstel geselecteerde en toegepaste periode naar het volledige bereik."""
    full_period = (
        period_min,
        period_max,
    )
    st.session_state["selected_period"] = full_period
    st.session_state["applied_period"] = full_period
