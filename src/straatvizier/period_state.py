import streamlit as st


def initialize_period_state(
    selected_street,
    comparison_street,
    compare,
    period_min,
    period_max,
):
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
    full_period = (
        period_min,
        period_max,
    )
    st.session_state["selected_period"] = full_period
    st.session_state["applied_period"] = full_period
