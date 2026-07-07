import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

st.set_page_config(page_title="LLM Red-Team Dashboard", layout="wide")
st.title("🛡️ LLM Red-Teaming Results")

json_files = sorted(RESULTS_DIR.glob("*.json"))
if not json_files:
    st.warning("No results found yet. Run a campaign first.")
    st.stop()

latest_file = json_files[-1]
results = json.loads(latest_file.read_text())
st.write(f"Loaded {len(results)} results from `{latest_file.name}`")

df = pd.DataFrame([{
    "category": r["category"],
    "topic": r["topic"],
    "final_verdict": r["final_verdict"],
    "rounds_taken": r["rounds_taken"],
} for r in results])

st.subheader("Attack Success Rate by Category")
asr = df.groupby("category")["final_verdict"].apply(lambda group: (group == "FAIL").mean())
st.bar_chart(asr)

st.subheader("All attempts")
st.dataframe(df, use_container_width=True)

st.subheader("Inspect a transcript")
labels = [f"{r['category']} / {r['topic']} → {r['final_verdict']}" for r in results]
idx = st.selectbox("Pick a result", range(len(results)), format_func=lambda i: labels[i])
chosen = results[idx]

for turn in chosen["history"]:
    with st.expander(f"Round {turn['round']} — verdict: {turn['verdict']}"):
        st.markdown("**Adversarial prompt:**")
        st.code(turn["prompt"])
        st.markdown("**Target response:**")
        st.code(turn["response"])
        st.markdown(f"**Judge reasoning:** {turn['reasoning']}")