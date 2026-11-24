"""Streamlit dashboard for CBSE Gazette exam results."""

import pandas as pd
import plotly.express as px
import streamlit as st

from exam_analysis import (
    GRADE_ORDER,
    answer_question,
    build_student_rows,
    build_subject_analysis,
    parse_cbse_gazette,
    performance_bands,
)


st.set_page_config(
    page_title="Exam Results | Performance report",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f4f7fc;
        color: #17233c;
    }
    [data-testid="stHeader"] { background: #f4f7fc; }
    [data-testid="stSidebar"] {
        background: #17233c;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #cbd5e1;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: #263650;
        border: 1px dashed #94a3b8;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        color: #17233c;
        background: #ffffff;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small {
        color: #e2e8f0;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d5deeb;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgb(23 35 60 / 5%);
    }
    [data-testid="stMetricLabel"] { color: #475569; }
    [data-testid="stMetricValue"] { color: #17233c; }
    h1, h2, h3, p, label { color: #17233c; }
    [data-testid="stCaptionContainer"] p { color: #475569; }
    [data-testid="stDataFrame"] {
        border: 1px solid #d5deeb;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("Exam report")
uploaded_file = st.sidebar.file_uploader(
    "Upload a CBSE Gazette text file",
    type=["txt"],
    help="The file is analyzed in this app session and is not sent to an AI service.",
)
st.sidebar.caption("Supports school / roll-number-wise CBSE Gazette .TXT files.")

st.title("Exam results, at a glance")
st.markdown(
    "Turn a CBSE result gazette into a clear performance report, grade breakdown, "
    "and answers to follow-up questions."
)

if uploaded_file is None:
    st.info("Upload a `.TXT` Gazette file in the sidebar to generate a report.")
    st.markdown(
        """
        **Your report includes**
        - Overall pass/result summary and best-five performance bands
        - Subject averages, score ranges, and grade distributions
        - Top performers and downloadable result tables
        - A local question box for exploring this file

        **Privacy:** analysis and question answering run in this app; no external AI
        service is used.
        """
    )
    st.stop()

try:
    report = parse_cbse_gazette(uploaded_file.getvalue().decode("utf-8", errors="replace"))
except (OSError, UnicodeError, ValueError) as error:
    st.error(f"Could not read this file: {error}")
    st.stop()

if not report.students:
    st.error(
        "No student records were found. Check that this is a CBSE school / "
        "roll-number-wise Gazette text file."
    )
    st.stop()

student_rows = build_student_rows(report)
students_df = pd.DataFrame(student_rows)
subject_rows = build_subject_analysis(report)
subjects_df = pd.DataFrame(subject_rows)
passed_students = [
    student
    for student in report.students
    if student.result.upper() == "PASS" and student.best_five_percentage is not None
]
pass_count = sum(student.result.upper() == "PASS" for student in report.students)
pass_rate = 100 * pass_count / len(report.students)
best_five_scores = [student.best_five_percentage for student in passed_students]
mean_best_five = (
    sum(best_five_scores) / len(best_five_scores) if best_five_scores else None
)

school_label = report.school_name or "School name not found"
metadata = " · ".join(
    value for value in (school_label, report.region, report.exam_date) if value
)
st.caption(metadata)
metric_columns = st.columns(4)
metric_columns[0].metric("Candidates", f"{len(report.students):,}")
metric_columns[1].metric("Passed", f"{pass_count:,}", f"{pass_rate:.1f}% pass rate")
metric_columns[2].metric(
    "Mean best-five",
    f"{mean_best_five:.1f}%" if mean_best_five is not None else "—",
    help="Average among passed candidates with five numeric subject marks.",
)
metric_columns[3].metric("Subjects", str(len(report.subject_codes)))

st.subheader("Performance overview")
overview_columns = st.columns(2)
result_counts = students_df["Result"].replace("", "Not stated").value_counts()
result_data = result_counts.rename_axis("Result").reset_index(name="Candidates")
with overview_columns[0]:
    st.markdown("**Result breakdown**")
    st.plotly_chart(
        px.pie(
            result_data,
            names="Result",
            values="Candidates",
            hole=0.58,
            color_discrete_sequence=["#4f46e5", "#f59e0b", "#94a3b8", "#ef4444"],
        ),
        use_container_width=True,
    )
with overview_columns[1]:
    st.markdown("**Passed candidates by best-five score**")
    band_data = pd.DataFrame(
        {
            "Performance band": list(performance_bands(report)),
            "Candidates": list(performance_bands(report).values()),
        }
    )
    st.plotly_chart(
        px.bar(
            band_data,
            x="Performance band",
            y="Candidates",
            color="Candidates",
            color_continuous_scale=["#c7d2fe", "#4f46e5"],
        ).update_layout(coloraxis_showscale=False),
        use_container_width=True,
    )

st.subheader("Subject performance")
scored_subjects = subjects_df.dropna(subset=["Mean_Marks"]).sort_values("Mean_Marks")
if not scored_subjects.empty:
    st.plotly_chart(
        px.bar(
            scored_subjects,
            x="Mean_Marks",
            y="Subject_Name",
            orientation="h",
            text="Mean_Marks",
            hover_data=["Students_Appeared", "Highest_Marks", "Lowest_Marks", "Pass_Percentage"],
            labels={"Mean_Marks": "Average marks", "Subject_Name": "Subject"},
            color="Mean_Marks",
            color_continuous_scale=["#c7d2fe", "#4f46e5"],
        )
        .update_traces(texttemplate="%{text:.1f}", textposition="outside")
        .update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"}),
        use_container_width=True,
    )
else:
    st.info("No numeric subject marks were found to compare.")

if not scored_subjects.empty:
    strongest = scored_subjects.iloc[-1]
    weakest = scored_subjects.iloc[0]
    distinction_count = performance_bands(report)["90% and above"]
    st.info(
        f"Highest subject average: **{strongest['Subject_Name']} "
        f"({strongest['Mean_Marks']:.1f})**. Lowest: **{weakest['Subject_Name']} "
        f"({weakest['Mean_Marks']:.1f})**. **{distinction_count}** passed "
        "candidate(s) scored 90% or higher in their best five."
    )

grade_tab, top_tab, detail_tab = st.tabs(
    ["Grade distribution", "Top performers", "Candidate results"]
)
with grade_tab:
    grade_subject = st.selectbox(
        "Choose a subject",
        options=report.subject_codes,
        format_func=lambda code: f"{code} · {next(row['Subject_Name'] for row in subject_rows if row['Subject_Code'] == code)}",
    )
    grade_row = next(row for row in subject_rows if row["Subject_Code"] == grade_subject)
    grade_data = pd.DataFrame(
        [
            {"Grade": grade, "Candidates": grade_row["Grade_" + grade]}
            for grade in GRADE_ORDER
            if grade_row["Grade_" + grade]
        ]
    )
    if grade_data.empty:
        st.info("No subject grades were recorded for this subject.")
    else:
        st.plotly_chart(
            px.bar(
                grade_data,
                x="Grade",
                y="Candidates",
                text="Candidates",
                category_orders={"Grade": GRADE_ORDER},
                color="Candidates",
                color_continuous_scale=["#c7d2fe", "#4f46e5"],
            )
            .update_traces(textposition="outside")
            .update_layout(coloraxis_showscale=False),
            use_container_width=True,
        )
    st.dataframe(
        subjects_df[
            [
                "Subject_Code",
                "Subject_Name",
                "Students_Enrolled",
                "Students_Appeared",
                "Mean_Marks",
                "Highest_Marks",
                "Lowest_Marks",
                "Pass_Count",
                "Pass_Percentage",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
with top_tab:
    top_df = (
        students_df[students_df["Result"].str.upper() == "PASS"]
        .dropna(subset=["Best5_Percentage"])
        .sort_values(["Best5_Percentage", "Total_Marks_All"], ascending=False)
        .head(10)
    )
    st.dataframe(
        top_df[
            [
                "Rank_Best5",
                "Roll_No",
                "Candidate_Name",
                "Best5_Total_500",
                "Best5_Percentage",
                "Total_Marks_All",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
with detail_tab:
    statuses = ["All"] + sorted(
        status for status in students_df["Result"].replace("", "Not stated").unique()
    )
    selected_status = st.selectbox("Filter by result", statuses)
    filtered_students = students_df.copy()
    if selected_status != "All":
        filtered_students["Result"] = filtered_students["Result"].replace("", "Not stated")
        filtered_students = filtered_students[filtered_students["Result"] == selected_status]
    st.dataframe(filtered_students, hide_index=True, use_container_width=True)

st.subheader("Ask about this result file")
st.caption(
    "Answers are calculated locally from the uploaded file. Try a candidate name or roll "
    "number, a subject average/pass rate, grade distribution, result breakdown, "
    "performance bands, or top performers."
)
with st.form("question_form"):
    question = st.text_input(
        "What would you like to analyze?",
        placeholder="For example: Which subject has the highest average?",
    )
    ask_clicked = st.form_submit_button("Analyze question", type="primary")

if ask_clicked:
    response = answer_question(report, question)
    st.markdown("**" + response["message"] + "**")
    if "subject" in response:
        subject = response["subject"]
        st.dataframe(pd.DataFrame([subject]), hide_index=True, use_container_width=True)
        question_grade_data = pd.DataFrame(
            [
                {"Grade": grade, "Candidates": subject["Grade_" + grade]}
                for grade in GRADE_ORDER
                if subject["Grade_" + grade]
            ]
        )
        if not question_grade_data.empty:
            st.bar_chart(question_grade_data.set_index("Grade"))
    if "subjects" in response:
        st.dataframe(pd.DataFrame(response["subjects"]), hide_index=True, use_container_width=True)
    if "students" in response:
        matched_rows = [
            row for row in student_rows if any(row["Roll_No"] == student.roll_no for student in response["students"])
        ]
        st.dataframe(pd.DataFrame(matched_rows), hide_index=True, use_container_width=True)
    if "grades" in response:
        grades_df = pd.DataFrame(
            [{"Grade": grade, "Count": count} for grade, count in response["grades"].items() if count]
        )
        if not grades_df.empty:
            st.bar_chart(grades_df.set_index("Grade"))
    if "bands" in response:
        st.bar_chart(
            pd.DataFrame(
                [{"Performance band": band, "Candidates": count} for band, count in response["bands"].items()]
            ).set_index("Performance band")
        )
    if "results" in response:
        st.dataframe(
            pd.DataFrame(
                [{"Result": result, "Candidates": count} for result, count in response["results"].items()]
            ),
            hide_index=True,
            use_container_width=True,
        )

st.subheader("Download report data")
download_columns = st.columns(2)
download_columns[0].download_button(
    "Download complete results (CSV)",
    data=students_df.to_csv(index=False).encode("utf-8"),
    file_name="complete_exam_results.csv",
    mime="text/csv",
)
download_columns[1].download_button(
    "Download subject analysis (CSV)",
    data=subjects_df.to_csv(index=False).encode("utf-8"),
    file_name="subject_analysis.csv",
    mime="text/csv",
)
