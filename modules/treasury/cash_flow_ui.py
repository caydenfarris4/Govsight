"""
Cash Flow Forecast tab (Navi).

Renders the CashFlowEngine projection: 12-month balance outlook, the
13-week near-term view, and the investable-surplus buckets that connect
directly to the Investment Optimizer.
"""

import streamlit as st
import plotly.graph_objects as go

from modules.treasury.cash_flow_engine import CashFlowEngine


def render_cash_flow_forecast(org: str = "cityA", org_display_name: str = ""):
    st.markdown("### Cash Flow Forecast")
    st.caption(
        "Projects monthly receipts and disbursements using each account "
        "type's historical monthly pattern, then walks the cash balance "
        "forward. Answers: when is cash tight, and how much can be invested "
        "for how long without breaching the operating floor.")

    col1, col2, col3 = st.columns(3)
    with col1:
        starting_balance = st.number_input(
            "Current cash balance ($)", min_value=0.0, value=8_000_000.0,
            step=250_000.0, format="%.0f",
            help="Total operating cash across bank accounts today")
    with col2:
        policy_floor = st.number_input(
            "Minimum operating floor ($)", min_value=0.0, value=4_000_000.0,
            step=250_000.0, format="%.0f",
            help="The balance you never want to dip below (reserve policy / "
                 "about one month of disbursements is a common floor)")
    with col3:
        revenue_scale = st.slider(
            "Revenue stress (%)", 80, 110, 100,
            help="Stress-test: project receipts at a percentage of budget "
                 "(90% simulates a revenue shortfall)") / 100.0

    engine = CashFlowEngine()
    proj = engine.project(starting_balance=starting_balance,
                          policy_floor=policy_floor,
                          revenue_scale=revenue_scale)

    if proj.method == "uniform":
        st.warning(
            "No monthly history found - flows are spread evenly across "
            "months. Connect monthly GL history (or run the sample seeder) "
            "for seasonality-aware projections.")
    else:
        st.success("Projection uses historical monthly seasonality from the general ledger.")

    # Headline numbers
    m1, m2, m3 = st.columns(3)
    m1.metric("Lowest projected balance",
              f"${proj.min_balance:,.0f}", proj.min_balance_month)
    m2.metric("Months below floor", len(proj.months_below_floor),
              delta=None if not proj.months_below_floor else ", ".join(proj.months_below_floor[:3]),
              delta_color="inverse")
    m3.metric("Investable for 12 months",
              f"${proj.investable.get('term_365d', 0):,.0f}")

    if proj.months_below_floor:
        st.error(
            "Projected balance drops below the operating floor in: "
            + ", ".join(proj.months_below_floor)
            + ". Plan short-term liquidity (delay discretionary spend, draw "
              "on LGIP) before those months.")

    # Monthly balance chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=proj.months, y=proj.receipts, name="Receipts",
                         marker_color="#2e7d32"))
    fig.add_trace(go.Bar(x=proj.months, y=[-d for d in proj.disbursements],
                         name="Disbursements", marker_color="#c62828"))
    fig.add_trace(go.Scatter(x=proj.months, y=proj.ending_balance,
                             name="Ending balance", mode="lines+markers",
                             line=dict(color="#12263a", width=3)))
    fig.add_hline(y=policy_floor, line_dash="dash", line_color="#8a5a12",
                  annotation_text="Operating floor")
    fig.update_layout(barmode="relative", height=420,
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True, key="cashflow_monthly")

    # Investable surplus -> investment optimizer hand-off
    st.markdown("#### How much can be invested")
    st.caption(
        "The amount safe to lock up for each horizon is the minimum "
        "projected surplus above the floor across that window.")
    inv = proj.investable
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Liquid (30 days)", f"${inv.get('liquid_30d', 0):,.0f}")
    c2.metric("90-day term", f"${inv.get('term_90d', 0):,.0f}")
    c3.metric("180-day term", f"${inv.get('term_180d', 0):,.0f}")
    c4.metric("12-month term", f"${inv.get('term_365d', 0):,.0f}")
    st.info("Compare these amounts against current rates in the Investment "
            "Optimizer tab to pick instruments per horizon.")

    # 13-week near-term view
    with st.expander("13-week near-term view"):
        st.caption(
            "Weekly figures are interpolated from the monthly projection "
            "(4-4-5 weeks). They become transaction-accurate once "
            "transaction-level history is connected through the data adapter.")
        wk = engine.weekly_view(proj)
        wfig = go.Figure()
        wfig.add_trace(go.Scatter(x=wk["labels"], y=wk["ending_balance"],
                                  mode="lines+markers", name="Ending balance",
                                  line=dict(color="#2e6fa3")))
        wfig.add_hline(y=policy_floor, line_dash="dash", line_color="#8a5a12")
        wfig.update_layout(height=320, margin=dict(t=20, b=10))
        st.plotly_chart(wfig, use_container_width=True, key="cashflow_weekly")
