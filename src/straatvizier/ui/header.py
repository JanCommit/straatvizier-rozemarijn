import streamlit as st


IVORY = "#F4F1E8"
SAGE = "#C7D0C2"


def render_frozen_header(
    title,
    selected_street,
    valid_days,
    avg_uptime_text,
    start_hour,
    end_hour,
    uptime_pct,
    min_hours,
    direction_choice,
    main_first,
    main_last,
    compare,
    comparison_street,
    comparison_layout,
):
    comparison_note = (
        (
            f" · vergelijking met {comparison_street}"
            + (
                " · samen in één grafiek"
                if comparison_layout == "Samen in één grafiek"
                else ""
            )
        )
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
                height: 9.5rem;
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
                    height: 12rem;
                }}
            }}
        </style>

        <div class="sv-head">
            <div class="sv-title">
                {title} — {selected_street}
            </div>

            <div class="sv-context">
                Lokale Belgische tijd
                {start_hour:02d}:00–{end_hour:02d}:00
                · minimum uptime {uptime_pct}%
                · minimum {min_hours} geldige uren per dag
                · {direction_choice}
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
                        {valid_days}
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
