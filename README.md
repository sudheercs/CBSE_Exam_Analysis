# CBSE Exam Results Dashboard

A local Streamlit app that turns a CBSE school / roll-number-wise Gazette `.TXT`
file into an interactive performance report. It shows result and best-five
performance distributions, subject averages, grade distributions, top performers,
and downloadable CSVs. A question box answers common candidate-, subject-, and
grade-related questions using the uploaded file without calling an external AI
service.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, then upload a `.TXT` Gazette file in
the sidebar.

For a safe sample, upload [`demo_data.txt`](./demo_data.txt). It contains 200
synthetic candidates across eight subjects, with pass, compartment, and
withheld-result examples. All names, roll numbers, and marks are fictional;
there are no real school or student records.

Question answering supports candidate names or roll numbers, subject averages,
highest/lowest subjects, subject grade counts and pass rates, overall grade
distribution, result breakdown, performance bands, and top performers.
