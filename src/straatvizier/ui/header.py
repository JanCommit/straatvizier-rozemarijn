"""Render de vaste dashboardheader met de actuele analysecontext."""

import streamlit as st


IVORY = "#F7F8F7"
PETROL = "#6DB7C4"
PETROL_STRONG = "#287A8B"



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
    """Render een compacte, sticky dashboardheader met kern-KPI's."""

    _ = min_hours  # bewust niet meer zichtbaar in de header

    title_context = (
        f"{selected_street} vs. {comparison_street}"
        if compare and comparison_street
        else selected_street
    )

    comparison_note = (
        (
            " · samen in één grafiek"
            if comparison_layout == "Samen in één grafiek"
            else " · onder elkaar"
        )
        if compare
        else ""
    )

    uptime_value = 0.0
    uptime_available = False

    if isinstance(avg_uptime_text, str) and avg_uptime_text.endswith("%"):
        try:
            uptime_value = float(
                avg_uptime_text[:-1].replace(",", ".")
            )
            uptime_value = max(0.0, min(100.0, uptime_value))
            uptime_available = True
        except ValueError:
            pass

    uptime_ring = (
        f"""
        <div class="sv-uptime-ring"
             style="--uptime:{uptime_value * 3.6:.1f}deg;"></div>
        """
        if uptime_available
        else '<div class="sv-uptime-ring sv-uptime-empty"></div>'
    )

    st.html(
        f"""
        <style>
            .sv-head {{
                position: fixed;
                top: 3.55rem;
                left: 19rem;
                right: 1rem;
                z-index: 9999;
                box-sizing: border-box;
                background: linear-gradient(180deg, #2D3338 0%, #292E33 100%);
                border: 1px solid rgba(255,255,255,.08);
                border-radius: 10px;
                padding: .78rem 1rem .68rem 5rem;
                margin-bottom: 1rem;
                box-shadow: 0 6px 18px rgba(0,0,0,.11);
            }}

            .sv-title {{
                font-size: 1.24rem;
                font-weight: 700;
                line-height: 1.2;
                color: {IVORY};
                margin: 0 0 .64rem 0;
                letter-spacing: -.01em;
            }}

            .sv-metrics {{
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 0;
                margin-bottom: .60rem;
            }}

            .sv-metric {{
                display: flex;
                align-items: center;
                gap: .52rem;
                padding: 0 1.3rem;
                min-height: 2.45rem;
                border-right: 1px solid rgba(109,183,196,.20);
            }}

            .sv-metric:first-child {{
                padding-left: 0;
            }}

            .sv-metric:last-child {{
                border-right: 0;
                padding-right: 0;
            }}

            .sv-icon {{
                width: 1.02rem;
                height: 1.02rem;
                color: {PETROL};
                flex: 0 0 auto;
                opacity: .95;
            }}

            .sv-kpi-copy {{
                display: flex;
                flex-direction: column;
                line-height: 1.06;
                min-width: 0;
            }}

            .sv-label {{
                font-size: .68rem;
                color: rgba(109,183,196,.92);
                margin-bottom: .18rem;
                white-space: nowrap;
            }}

            .sv-value {{
                font-size: 1rem;
                font-weight: 680;
                color: {IVORY};
                white-space: nowrap;
            }}

            .sv-uptime-wrap {{
                display: flex;
                align-items: center;
                gap: .52rem;
            }}

            .sv-uptime-ring {{
                --uptime: 0deg;
                width: 1.42rem;
                height: 1.42rem;
                border-radius: 50%;
                background: conic-gradient(
                    {PETROL_STRONG} var(--uptime),
                    rgba(40,122,139,.20) 0
                );
                position: relative;
                flex: 0 0 auto;
            }}

            .sv-uptime-ring::after {{
                content: "";
                position: absolute;
                inset: .23rem;
                border-radius: 50%;
                background: #2D3338;
            }}

            .sv-uptime-empty {{
                background: rgba(109,183,196,.20);
            }}

            .sv-spacer {{
                height: 8.4rem;
            }}

            .sv-context {{
                font-size: .76rem;
                color: rgba(219,239,242,.82);
                padding-top: .52rem;
                border-top: 1px solid rgba(109,183,196,.18);
                line-height: 1.35;
            }}

            @media(max-width:1100px) {{
                .sv-metric {{
                    padding: 0 .9rem;
                }}
            }}

            @media(max-width:900px) {{
                .sv-head {{
                    top: 3.4rem;
                    left: 1rem;
                    right: 1rem;
                    padding: .78rem .85rem .7rem;
                }}

                .sv-spacer {{
                    height: 11.5rem;
                }}

                .sv-metrics {{
                    row-gap: .72rem;
                }}

                .sv-metric {{
                    min-width: calc(50% - 1rem);
                    padding: 0 .8rem;
                }}

                .sv-metric:nth-child(2) {{
                    border-right: 0;
                }}

                .sv-metric:nth-child(3) {{
                    padding-left: 0;
                }}
            }}
        </style>

        <div class="sv-head">
            <div class="sv-title">
                {title} — {title_context}
            </div>

            <div class="sv-metrics">
                <div class="sv-metric">
                    <svg class="sv-icon" viewBox="0 0 24 24"
                         fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round"
                         stroke-linejoin="round" aria-hidden="true">
                        <rect x="3" y="5" width="18" height="16" rx="2"></rect>
                        <path d="M16 3v4M8 3v4M3 10h18"></path>
                    </svg>
                    <div class="sv-kpi-copy">
                        <div class="sv-label">Eerste meting</div>
                        <div class="sv-value">
                            {main_first.strftime("%d/%m/%Y")}
                        </div>
                    </div>
                </div>

                <div class="sv-metric">
                    <svg class="sv-icon" viewBox="0 0 24 24"
                         fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round"
                         stroke-linejoin="round" aria-hidden="true">
                        <rect x="3" y="5" width="18" height="16" rx="2"></rect>
                        <path d="M16 3v4M8 3v4M3 10h18"></path>
                        <path d="M15 14l2 2 4-4"></path>
                    </svg>
                    <div class="sv-kpi-copy">
                        <div class="sv-label">Laatste meting</div>
                        <div class="sv-value">
                            {main_last.strftime("%d/%m/%Y")}
                        </div>
                    </div>
                </div>

                <div class="sv-metric">
                    <svg class="sv-icon" viewBox="0 0 24 24"
                         fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round"
                         stroke-linejoin="round" aria-hidden="true">
                        <path d="M4 12l5 5L20 6"></path>
                    </svg>
                    <div class="sv-kpi-copy">
                        <div class="sv-label">Geldige dagen</div>
                        <div class="sv-value">{valid_days}</div>
                    </div>
                </div>

                <div class="sv-metric">
                    <div class="sv-uptime-wrap">
                        {uptime_ring}
                        <div class="sv-kpi-copy">
                            <div class="sv-label">Gem. uptime</div>
                            <div class="sv-value">{avg_uptime_text}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="sv-context">
                Lokale Belgische tijd
                {start_hour:02d}:00–{end_hour:02d}:00
                · minimum uptime {uptime_pct}%
                · {direction_choice}
                {comparison_note}
            </div>
        </div>

        <div class="sv-spacer"></div>
        """
    )
