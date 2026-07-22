"""
Admin panel: AI Data Mapping (the data massaging layer).

Lets an administrator register data sources (ERP REST APIs, CSV exports,
the Caselle adapter), have the AI propose a mapping from the source's
fields into GovSight's canonical schema, review and approve that mapping,
and run syncs that funnel massaged data into the canonical store every
module reads.

Rendered as a tab inside the ERP Integration Hub.
"""

import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from modules.data_adapter.ai_data_mapper import (
    MappingStore,
    SUPPORTED_TRANSFORMS,
)
from modules.data_adapter.canonical_schema import CANONICAL_ENTITIES
from modules.data_adapter.ingestion_pipeline import IngestionPipeline


def _pipeline() -> IngestionPipeline:
    if "ai_ingestion_pipeline" not in st.session_state:
        st.session_state.ai_ingestion_pipeline = IngestionPipeline()
    return st.session_state.ai_ingestion_pipeline


def render_data_integration_panel():
    st.subheader("AI Data Mapping")
    st.markdown(
        "Connect data from any ERP or export format. GovSight profiles the "
        "source, proposes a field mapping into its canonical schema (AI-assisted "
        "when an AI key is configured), and after your approval, syncs flow "
        "through that mapping into the platform's data store."
    )

    pipe = _pipeline()
    store: MappingStore = pipe.store

    tab_sources, tab_map, tab_sync, tab_history = st.tabs(
        ["Sources", "Propose & Approve Mapping", "Run Sync", "Sync History"])

    with tab_sources:
        _render_sources(store)
    with tab_map:
        _render_mapping_workflow(pipe, store)
    with tab_sync:
        _render_sync(pipe, store)
    with tab_history:
        _render_history(store)


# ---------------------------------------------------------------------------

def _render_sources(store: MappingStore):
    sources = store.list_sources()
    if sources:
        st.dataframe(pd.DataFrame(
            [{"Name": s["name"], "Type": s["source_type"],
              "Config": json.dumps({k: v for k, v in s["config"].items()
                                    if k not in ("bearer_token", "content")})[:80]}
             for s in sources]),
            use_container_width=True, hide_index=True)
    else:
        st.info("No data sources registered yet.")

    with st.expander("Register a new source"):
        name = st.text_input("Source name", placeholder="e.g. Tyler Munis GL Export")
        stype = st.selectbox("Source type", ["rest_api", "csv", "caselle"],
                             format_func={"rest_api": "REST API",
                                          "csv": "CSV file",
                                          "caselle": "Caselle adapter"}.get)
        config: Dict[str, Any] = {}
        if stype == "rest_api":
            config["url"] = st.text_input("Endpoint URL", placeholder="https://erp.example.gov/api/gl")
            config["records_key"] = st.text_input(
                "Record list key (optional)", placeholder="data",
                help="If the API wraps records in an object, the key that holds the list")
            token_env = st.text_input(
                "Token environment variable (optional)", placeholder="MUNIS_API_TOKEN",
                help="Name of an environment variable holding the bearer token. "
                     "Tokens are never stored in the mapping database.")
            if token_env:
                config["token_env"] = token_env
        elif stype == "csv":
            uploaded = st.file_uploader("Upload a CSV export", type=["csv"], key="src_csv")
            if uploaded is not None:
                config["content"] = uploaded.getvalue().decode("utf-8-sig")
                st.caption(f"{uploaded.name}: {len(config['content'].splitlines()) - 1} data rows")
            config["path"] = st.text_input(
                "...or a server file path (optional)",
                help="For recurring drops, e.g. a watched folder path")
        else:
            config["municipality_id"] = st.text_input("Municipality ID", value="default")
            config["dataset"] = st.selectbox("Dataset", [
                "general_ledger", "budget", "payroll",
                "accounts_payable", "vendors", "departments"])

        if st.button("Register source", type="primary", disabled=not name):
            store.register_source(name, stype, config)
            st.success(f"Registered source: {name}")
            st.rerun()


# ---------------------------------------------------------------------------

def _render_mapping_workflow(pipe: IngestionPipeline, store: MappingStore):
    sources = store.list_sources()
    if not sources:
        st.info("Register a source first.")
        return

    source = st.selectbox("Source", sources, format_func=lambda s: s["name"], key="map_src")
    entity = st.selectbox("Canonical entity (what this data is)",
                          list(CANONICAL_ENTITIES),
                          format_func=lambda e: f"{e} — {CANONICAL_ENTITIES[e].description}",
                          key="map_entity")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Propose mapping", type="primary"):
            with st.spinner("Profiling sample and proposing mapping..."):
                try:
                    proposal = pipe.propose_mapping(
                        source["name"], source["source_type"], entity,
                        config=source["config"])
                    st.session_state["active_proposal"] = proposal
                except Exception as exc:
                    st.error(f"Could not propose mapping: {exc}")
    with col2:
        st.caption(
            "With an OpenAI or Anthropic key configured, the proposal is "
            "AI-generated from field names, types, and sample values. Without "
            "one, a deterministic name-matching heuristic is used. Either way "
            "you review and approve before any data flows.")

    proposal = st.session_state.get("active_proposal")
    if not proposal or proposal.get("entity") != entity:
        # Show existing approved mapping status for context
        approved = store.get_approved_mapping(source["id"], entity)
        if approved:
            st.success(
                f"Approved mapping v{approved['version']} in place "
                f"(method: {approved['method']}, approved by "
                f"{approved['approved_by']} at {approved['approved_at'][:19]})")
        return

    method_label = {"ai": "AI-proposed", "heuristic": "Heuristic (no AI key configured)",
                    "manual": "Manually edited"}.get(proposal["method"], proposal["method"])
    st.markdown(f"**Proposal** — {method_label}")

    if proposal.get("unmapped_required"):
        st.error("Required fields with no proposed source: "
                 + ", ".join(proposal["unmapped_required"])
                 + ". Edit the table below to fill them in before approving.")
    if proposal.get("needs_review"):
        st.warning("Low-confidence mappings needing review: "
                   + ", ".join(proposal["needs_review"]))

    edited = st.data_editor(
        pd.DataFrame([{
            "Target": m["target"],
            "Source field(s)": json.dumps(m["source"]) if isinstance(m["source"], list) else m["source"],
            "Transform": m["transform"],
            "Params (JSON)": json.dumps(m.get("params") or {}),
            "Confidence": m["confidence"],
            "Note": m.get("note", ""),
        } for m in proposal["mappings"]]),
        column_config={
            "Transform": st.column_config.SelectboxColumn(
                options=list(SUPPORTED_TRANSFORMS)),
            "Confidence": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        },
        num_rows="dynamic", use_container_width=True, hide_index=True,
        key="mapping_editor")

    with st.expander("Source sample profile"):
        st.dataframe(pd.DataFrame(proposal["profiled_fields"]),
                     use_container_width=True, hide_index=True)

    if st.button("Approve mapping", type="primary"):
        try:
            mappings = _editor_to_mappings(edited)
            user = st.session_state.get("username", "admin")
            store.approve_mapping(proposal["mapping_id"], approved_by=user,
                                  edited_mappings=mappings)
            del st.session_state["active_proposal"]
            st.success("Mapping approved. Syncs for this source now flow through it.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not approve: {exc}")


def _editor_to_mappings(df: pd.DataFrame) -> List[Dict[str, Any]]:
    mappings = []
    for _, row in df.iterrows():
        source_raw = str(row["Source field(s)"]).strip()
        try:
            source = json.loads(source_raw) if source_raw.startswith("[") else source_raw
        except json.JSONDecodeError:
            source = source_raw
        try:
            params = json.loads(str(row["Params (JSON)"]) or "{}")
        except json.JSONDecodeError:
            params = {}
        if not row["Target"] or not str(row["Target"]).strip():
            continue
        mappings.append({
            "target": str(row["Target"]).strip(),
            "source": source,
            "transform": str(row["Transform"]).strip() or "direct",
            "params": params,
            "confidence": float(row.get("Confidence") or 1.0),
            "note": str(row.get("Note") or ""),
        })
    return mappings


# ---------------------------------------------------------------------------

def _render_sync(pipe: IngestionPipeline, store: MappingStore):
    sources = store.list_sources()
    if not sources:
        st.info("Register a source first.")
        return
    source = st.selectbox("Source", sources, format_func=lambda s: s["name"], key="sync_src")
    entity = st.selectbox("Entity", list(CANONICAL_ENTITIES), key="sync_entity")

    approved = store.get_approved_mapping(source["id"], entity)
    if approved is None:
        st.warning("No approved mapping for this source/entity yet — approve one "
                   "in the previous tab first.")
        return
    st.caption(f"Will use approved mapping v{approved['version']} ({approved['method']}).")

    if st.button("Run sync now", type="primary"):
        with st.spinner("Fetching, massaging, and writing canonical records..."):
            try:
                result = pipe.run_sync(source["name"], entity)
                col1, col2, col3 = st.columns(3)
                col1.metric("Rows fetched", result["total"])
                col2.metric("Written to canonical store", result.get("written", 0))
                col3.metric("Row errors", result["failed"])
                if result["errors"]:
                    with st.expander(f"Row errors ({result['failed']})"):
                        for err in result["errors"][:50]:
                            st.text(f"row {err['row']}: {'; '.join(err['errors'])}")
            except Exception as exc:
                st.error(f"Sync failed: {exc}")


def _render_history(store: MappingStore):
    syncs = store.recent_syncs()
    if not syncs:
        st.info("No syncs have run yet.")
        return
    st.dataframe(pd.DataFrame([{
        "Source": s["source_name"], "Entity": s["entity"],
        "Started": (s["started_at"] or "")[:19],
        "Status": s["status"], "Fetched": s["total"],
        "OK": s["succeeded"], "Failed": s["failed"],
    } for s in syncs]), use_container_width=True, hide_index=True)
