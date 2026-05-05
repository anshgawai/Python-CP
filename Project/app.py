from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


BASE_DIR = Path(__file__).parent
APP_PORT = 8507
COLOR_SEQUENCE = ["#2563eb", "#16a34a", "#7c3aed", "#f97316", "#db2777"]
PAGES = [
    "Dashboard",
    "Visualizations",
    "Upload Dataset",
    "Insights",
    "Correlation",
    "Reports",
]


st.set_page_config(
    page_title="Data Visualizer",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_text(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def inject_assets() -> None:
    st.markdown(f"<style>{load_text('styles.css')}</style>", unsafe_allow_html=True)
    components.html(f"<script>{load_text('script.js')}</script>", height=0, width=0)


@st.cache_data
def generate_sample_data(rows: int = 220) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    education_levels = np.array(["High School", "Bachelor", "Master", "PhD"])
    education_weights = np.array([0.28, 0.42, 0.23, 0.07])

    age = rng.integers(21, 61, rows)
    education = rng.choice(education_levels, size=rows, p=education_weights)
    experience = np.clip(age - rng.integers(19, 27, rows), 0, 38)

    education_bonus = pd.Series(education).map(
        {
            "High School": 0,
            "Bachelor": 9500,
            "Master": 18000,
            "PhD": 26000,
        }
    ).to_numpy()

    income = (
        29000
        + experience * 2100
        + education_bonus
        + rng.normal(0, 8500, rows)
    )
    income = np.clip(income, 26000, 185000).round(0)

    score = (
        48
        + experience * 0.7
        + (income - income.mean()) / 3500
        + rng.normal(0, 7, rows)
    )
    score = np.clip(score, 20, 100).round(1)

    data = pd.DataFrame(
        {
            "Age": age,
            "Income": income.astype(float),
            "Education": education,
            "Experience": experience,
            "Score": score,
        }
    )

    missing_income = rng.choice(data.index, size=5, replace=False)
    missing_score = rng.choice(data.index.difference(missing_income), size=4, replace=False)
    data.loc[missing_income, "Income"] = np.nan
    data.loc[missing_score, "Score"] = np.nan
    return data


def get_dataset() -> pd.DataFrame:
    if "dataset" not in st.session_state:
        st.session_state.dataset = generate_sample_data()
        st.session_state.dataset_name = "Default sample dataset"
    return st.session_state.dataset


def get_current_page() -> str:
    requested = st.query_params.get("page", "Dashboard")
    if requested not in PAGES:
        return "Dashboard"
    return requested


def render_navbar(active_page: str) -> None:
    links = []
    for page in PAGES:
        active_class = " active" if page == active_page else ""
        links.append(
            f'<a class="nav-link{active_class}" href="?page={quote_plus(page)}" '
            f'data-page="{page}">{page}</a>'
        )

    html = load_text("navbar.html")
    html = html.replace("{{NAV_LINKS}}", "\n".join(links))
    html = html.replace("{{ACTIVE_PAGE}}", active_page)
    st.markdown(html, unsafe_allow_html=True)


def page_title(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <section class="page-heading">
            <div>
                <p>{subtitle}</p>
                <h1>{title}</h1>
            </div>
             <span>Professional analytics workspace</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str) -> str:
    return f"""
    <div class="metric-card">
        <span>{label}</span>
        <strong>{value}</strong>
    </div>
    """


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=np.number).columns.tolist()


def missing_percent(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return (df.isna().sum().sum() / df.size) * 100


def chart_layout(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111", family="Arial"),
        title=dict(font=dict(size=18, color="#111111"), x=0.02, xanchor="left"),
        margin=dict(l=38, r=24, t=58, b=42),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#111111", font_color="#ffffff", bordercolor="#111111"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#ededed", zeroline=False, linecolor="#111111")
    fig.update_yaxes(showgrid=True, gridcolor="#ededed", zeroline=False, linecolor="#111111")
    return fig


def render_plot(fig: go.Figure, height: int = 380) -> None:
    st.plotly_chart(
        chart_layout(fig, height),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def scatter_size_column(df: pd.DataFrame) -> str | None:
    if "Score" not in df.columns or not pd.api.types.is_numeric_dtype(df["Score"]):
        return None

    size_column = "Score Size"
    df[size_column] = df["Score"].fillna(df["Score"].median())
    df[size_column] = df[size_column].fillna(12).clip(lower=1)
    return size_column


def render_dashboard(df: pd.DataFrame) -> None:
    page_title("Dashboard", "Clean dataset overview")

    nums = numeric_columns(df)
    cards = [
        metric_card("Total Rows", f"{len(df):,}"),
        metric_card("Total Columns", f"{len(df.columns):,}"),
        metric_card("Numeric Columns", f"{len(nums):,}"),
        metric_card("Missing Values", f"{missing_percent(df):.1f}%"),
    ]
    st.markdown(f"<div class='metric-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)

    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        st.markdown("<div class='section-label'>Dataset Preview</div>", unsafe_allow_html=True)
        st.dataframe(df.head(8), use_container_width=True, hide_index=True)

    with right:
        if "Income" in df.columns:
            fig = px.histogram(
                df,
                x="Income",
                nbins=24,
                color_discrete_sequence=["#2563eb"],
                title="Income Distribution",
            )
            fig.update_traces(marker_line_color="#ffffff", marker_line_width=1)
            render_plot(fig, 320)
        else:
            st.info("Income column not found in the current dataset.")

    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        if "Education" in df.columns:
            education_counts = df["Education"].fillna("Missing").value_counts().reset_index()
            education_counts.columns = ["Education", "Count"]
            fig = px.pie(
                education_counts,
                names="Education",
                values="Count",
                hole=0.5,
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Pie Chart: Education Mix",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label", marker_line_color="#ffffff")
            render_plot(fig, 360)

    with chart_right:
        if {"Age", "Income"}.issubset(df.columns):
            scatter_df = df.dropna(subset=["Age", "Income"]).copy()
            size_column = scatter_size_column(scatter_df)
            fig = px.scatter(
                scatter_df,
                x="Age",
                y="Income",
                color="Education" if "Education" in df.columns else None,
                size=size_column,
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Scatter Plot: Age vs Income",
            )
            fig.update_traces(marker=dict(line=dict(width=0.8, color="#111111"), opacity=0.82))
            render_plot(fig, 360)


def render_visualizations(df: pd.DataFrame) -> None:
    page_title("Visualizations", "Simple colored charts")

    top_left, top_right = st.columns(2, gap="large")
    with top_left:
        if "Income" in df.columns:
            fig = px.histogram(
                df,
                x="Income",
                nbins=28,
                color_discrete_sequence=["#2563eb"],
                title="Histogram: Income",
            )
            fig.update_traces(marker_line_color="#ffffff", marker_line_width=1)
            render_plot(fig)
        else:
            st.info("Income column not found.")

    with top_right:
        if {"Age", "Income"}.issubset(df.columns):
            scatter_df = df.dropna(subset=["Age", "Income"]).copy()
            size_column = scatter_size_column(scatter_df)
            fig = px.scatter(
                scatter_df,
                x="Age",
                y="Income",
                color="Education" if "Education" in df.columns else None,
                size=size_column,
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Scatter: Age vs Income",
            )
            fig.update_traces(marker=dict(line=dict(width=0.8, color="#111111"), opacity=0.82))
            render_plot(fig)
        else:
            st.info("Age and Income columns are needed for this scatter plot.")

    bottom_left, bottom_right = st.columns(2, gap="large")
    with bottom_left:
        if "Education" in df.columns:
            counts = df["Education"].fillna("Missing").value_counts().reset_index()
            counts.columns = ["Education", "Count"]
            fig = px.bar(
                counts,
                x="Education",
                y="Count",
                color="Education",
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Bar Chart: Education Counts",
            )
            fig.update_traces(marker_line_color="#111111", marker_line_width=0.6)
            render_plot(fig)
        else:
            st.info("Education column not found.")

    with bottom_right:
        if "Education" in df.columns:
            counts = df["Education"].fillna("Missing").value_counts().reset_index()
            counts.columns = ["Education", "Count"]
            fig = px.pie(
                counts,
                names="Education",
                values="Count",
                hole=0.48,
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Pie Chart: Education Share",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label", marker_line_color="#ffffff")
            render_plot(fig)


def render_upload(df: pd.DataFrame) -> None:
    page_title("Upload Dataset", "Upload CSV or keep the generated sample")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            st.session_state.dataset = uploaded_df
            st.session_state.dataset_name = uploaded_file.name
            df = uploaded_df
            st.success(f"Loaded {uploaded_file.name}")
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
    else:
        st.caption(f"Using: {st.session_state.get('dataset_name', 'Default sample dataset')}")

    st.markdown("<div class='section-label'>Current Dataset Preview</div>", unsafe_allow_html=True)
    st.dataframe(df.head(12), use_container_width=True, hide_index=True)


def strongest_correlation(df: pd.DataFrame) -> str:
    nums = numeric_columns(df)
    if len(nums) < 2:
        return "Not enough numeric columns to calculate correlations."

    signed_corr = df[nums].corr(numeric_only=True)
    corr = signed_corr.abs()
    np.fill_diagonal(corr.values, np.nan)
    ranked = corr.stack().dropna()
    if ranked.empty:
        return "Correlation insight unavailable because numeric columns are constant or empty."

    best_pair = ranked.idxmax()
    best_value = signed_corr.loc[best_pair[0], best_pair[1]]
    return f"Strongest numeric relationship: {best_pair[0]} and {best_pair[1]} ({best_value:.2f})."


def render_insights(df: pd.DataFrame) -> None:
    page_title("Insights", "Rule-based observations")

    insights = []
    if "Income" in df.columns and pd.api.types.is_numeric_dtype(df["Income"]):
        insights.append(f"Mean income is {df['Income'].mean():,.0f}.")
    else:
        insights.append("Income insight unavailable because no numeric Income column was found.")

    insights.append(strongest_correlation(df))

    missing_cells = int(df.isna().sum().sum())
    if missing_cells:
        insights.append(f"The dataset has {missing_cells:,} missing cells ({missing_percent(df):.1f}% overall).")
    else:
        insights.append("No missing values were found in the dataset.")

    nums = numeric_columns(df)
    insights.append(f"{len(nums)} numeric columns are available for charts and correlation checks.")

    bullet_html = "".join(f"<li>{item}</li>" for item in insights)
    st.markdown(f"<ul class='insight-list'>{bullet_html}</ul>", unsafe_allow_html=True)


def render_correlation(df: pd.DataFrame) -> None:
    page_title("Correlation", "Numeric relationship matrix")

    nums = numeric_columns(df)
    if len(nums) < 2:
        st.info("At least two numeric columns are needed for correlation analysis.")
        return

    corr = df[nums].corr(numeric_only=True)
    fig = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale=["#16a34a", "#ffffff", "#7c3aed"],
        title="Correlation Heatmap",
        zmin=-1,
        zmax=1,
    )
    render_plot(fig, 460)

    st.markdown("<div class='section-label'>Correlation Table</div>", unsafe_allow_html=True)
    st.dataframe(corr.round(2), use_container_width=True)


def render_reports(df: pd.DataFrame) -> None:
    page_title("Reports", "Compact export summary")

    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        st.markdown(
            f"""
            <div class="report-card">
                <span>Dataset Shape</span>
                <strong>{df.shape[0]:,} rows x {df.shape[1]:,} columns</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="ai_data_analyzer_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with right:
        chips = "".join(f"<span>{col}</span>" for col in df.columns)
        st.markdown(
            f"""
            <div class="columns-box">
                <p>Columns</p>
                <div>{chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    inject_assets()
    page = get_current_page()
    render_navbar(page)
    df = get_dataset()

    st.markdown("<main class='content-shell'>", unsafe_allow_html=True)
    if page == "Dashboard":
        render_dashboard(df)
    elif page == "Visualizations":
        render_visualizations(df)
    elif page == "Upload Dataset":
        render_upload(df)
    elif page == "Insights":
        render_insights(df)
    elif page == "Correlation":
        render_correlation(df)
    elif page == "Reports":
        render_reports(df)
    st.markdown("</main>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
