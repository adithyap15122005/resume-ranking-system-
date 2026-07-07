"""
Plotly chart builders for the Analytics dashboard.
Each function returns a Plotly figure ready to pass to st.plotly_chart().
"""
from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ── Colour palette ────────────────────────────────────────────────────────────

RECOMMENDATION_COLOURS = {
    "Excellent Candidate": "#2ecc71",
    "Strong Match": "#27ae60",
    "Suitable": "#f39c12",
    "Average Match": "#e67e22",
    "Not Recommended": "#e74c3c",
}


def score_bar_chart(results: List[Dict[str, Any]]) -> go.Figure:
    """Horizontal bar chart of candidate similarity scores."""
    df = pd.DataFrame(results)[["candidate_name", "similarity_score", "recommendation"]].copy()
    df = df.sort_values("similarity_score", ascending=True)
    df["colour"] = df["recommendation"].map(RECOMMENDATION_COLOURS).fillna("#95a5a6")

    fig = go.Figure(
        go.Bar(
            x=df["similarity_score"],
            y=df["candidate_name"],
            orientation="h",
            marker_color=df["colour"].tolist(),
            text=df["similarity_score"].apply(lambda s: f"{s:.1f}%"),
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Score: %{x:.2f}%<br>"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Candidate Similarity Scores",
        xaxis_title="Similarity Score (%)",
        yaxis_title="Candidate",
        xaxis=dict(range=[0, 105]),
        height=max(300, 40 * len(df)),
        margin=dict(l=160, r=60, t=50, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
    )
    return fig


def recommendation_pie(results: List[Dict[str, Any]]) -> go.Figure:
    """Pie chart of recommendation distribution."""
    df = pd.DataFrame(results)
    counts = df["recommendation"].value_counts().reset_index()
    counts.columns = ["recommendation", "count"]
    colours = [RECOMMENDATION_COLOURS.get(r, "#95a5a6") for r in counts["recommendation"]]

    fig = go.Figure(
        go.Pie(
            labels=counts["recommendation"],
            values=counts["count"],
            marker=dict(colors=colours),
            hovertemplate="%{label}: %{value} candidates (%{percent})<extra></extra>",
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        title="Recommendation Distribution",
        height=380,
        margin=dict(t=50, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def score_distribution(results: List[Dict[str, Any]]) -> go.Figure:
    """Histogram of similarity score distribution."""
    scores = [r["similarity_score"] for r in results]

    fig = go.Figure(
        go.Histogram(
            x=scores,
            nbinsx=20,
            marker_color="#3498db",
            marker_line_color="white",
            marker_line_width=1,
            hovertemplate="Score range: %{x}<br>Count: %{y}<extra></extra>",
        )
    )
    # Add threshold lines
    for threshold, label, colour in [
        (95, "Excellent", "#2ecc71"),
        (80, "Strong", "#27ae60"),
        (60, "Suitable", "#f39c12"),
        (40, "Average", "#e67e22"),
    ]:
        fig.add_vline(x=threshold, line_dash="dash", line_color=colour, annotation_text=label)

    fig.update_layout(
        title="Score Distribution",
        xaxis_title="Similarity Score (%)",
        yaxis_title="Number of Candidates",
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def skill_match_bar(results: List[Dict[str, Any]], top_n: int = 15) -> go.Figure:
    """Bar chart of most frequently matched skills across all candidates."""
    from collections import Counter
    all_matched = []
    for r in results:
        all_matched.extend(r.get("matched_skills", []))
    counts = Counter(all_matched).most_common(top_n)
    if not counts:
        return go.Figure()

    skills, freqs = zip(*counts)
    fig = go.Figure(
        go.Bar(
            x=list(freqs),
            y=list(skills),
            orientation="h",
            marker_color="#3498db",
            hovertemplate="%{y}: found in %{x} resumes<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Top {top_n} Matched Skills",
        xaxis_title="Number of Candidates",
        yaxis_title="Skill",
        height=max(300, 35 * top_n),
        margin=dict(l=160, r=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def missing_skill_bar(results: List[Dict[str, Any]], top_n: int = 15) -> go.Figure:
    """Bar chart showing most frequently missing skills."""
    from collections import Counter
    all_missing = []
    for r in results:
        all_missing.extend(r.get("missing_skills", []))
    counts = Counter(all_missing).most_common(top_n)
    if not counts:
        return go.Figure()

    skills, freqs = zip(*counts)
    fig = go.Figure(
        go.Bar(
            x=list(freqs),
            y=list(skills),
            orientation="h",
            marker_color="#e74c3c",
            hovertemplate="%{y}: missing in %{x} resumes<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Top {top_n} Missing Skills (skill gaps)",
        xaxis_title="Number of Candidates",
        yaxis_title="Skill",
        height=max(300, 35 * top_n),
        margin=dict(l=160, r=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def experience_scatter(results: List[Dict[str, Any]]) -> go.Figure:
    """Scatter plot: experience years vs similarity score."""
    df = pd.DataFrame(results)
    if "experience_years" not in df.columns:
        return go.Figure()

    df["colour"] = df["recommendation"].map(RECOMMENDATION_COLOURS).fillna("#95a5a6")

    fig = go.Figure()
    for rec, colour in RECOMMENDATION_COLOURS.items():
        subset = df[df["recommendation"] == rec]
        if subset.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=subset["experience_years"],
                y=subset["similarity_score"],
                mode="markers+text",
                name=rec,
                text=subset["candidate_name"],
                textposition="top center",
                marker=dict(color=colour, size=12, line=dict(color="white", width=1)),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Experience: %{x} years<br>"
                    "Score: %{y:.1f}%<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title="Experience vs Similarity Score",
        xaxis_title="Years of Experience",
        yaxis_title="Similarity Score (%)",
        height=420,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def quality_gauge(score: float, candidate_name: str) -> go.Figure:
    """Gauge chart for a single candidate's quality/completeness score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            title={"text": f"Resume Quality<br><sub>{candidate_name}</sub>"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#3498db"},
                "steps": [
                    {"range": [0, 40], "color": "#fde8e8"},
                    {"range": [40, 70], "color": "#fef9e7"},
                    {"range": [70, 100], "color": "#e8f8f5"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
            number={"suffix": "%"},
        )
    )
    fig.update_layout(height=280, margin=dict(t=40, b=20, l=20, r=20))
    return fig
