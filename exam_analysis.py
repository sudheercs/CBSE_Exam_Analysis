"""Parsing and analysis helpers for CBSE school result gazette files."""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


CBSE_SUBJECT_CODES = {
    "001": "English Elective",
    "002": "Hindi Elective",
    "027": "History",
    "028": "Political Science",
    "029": "Geography",
    "030": "Economics",
    "037": "Psychology",
    "039": "Sociology",
    "041": "Mathematics",
    "042": "Physics",
    "043": "Chemistry",
    "044": "Biology",
    "048": "Physical Education",
    "049": "Painting",
    "054": "Business Studies",
    "055": "Accountancy",
    "064": "Home Science",
    "065": "Informatics Practices",
    "083": "Computer Science",
    "241": "Applied Mathematics",
    "301": "English Core",
    "302": "Hindi Core",
    "322": "Sanskrit Core",
}

GRADE_ORDER = [
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
    "D1",
    "D2",
    "E1",
    "E2",
    "E",
    "AB",
]
GRADE_PATTERN = re.compile(r"^(?:A[12]|B[12]|C[12]|D[12]|E[12]?)$")
STUDENT_LINE_PATTERN = re.compile(
    r"^\s*(\d{8})\s+([A-Z]?)\s+([MF])\s+(.+?)\s+"
    r"((?:\d{3}\s+){1,8})(.*)$"
)


@dataclass
class Student:
    roll_no: str
    name: str
    gender: str
    result: str
    compartment_subject: str
    internal_grades: List[str]
    subject_codes: List[str]
    marks: Dict[str, Optional[int]] = field(default_factory=dict)
    grades: Dict[str, str] = field(default_factory=dict)

    @property
    def total_marks(self) -> Optional[int]:
        scores = [mark for mark in self.marks.values() if mark is not None]
        return sum(scores) if scores else None

    @property
    def best_five_marks(self) -> Optional[int]:
        scores = sorted(
            (mark for mark in self.marks.values() if mark is not None),
            reverse=True,
        )
        return sum(scores[:5]) if len(scores) >= 5 else None

    @property
    def best_five_percentage(self) -> Optional[float]:
        total = self.best_five_marks
        return round(total / 5, 2) if total is not None else None

    @property
    def percentage_all(self) -> Optional[float]:
        scores = [mark for mark in self.marks.values() if mark is not None]
        return round(sum(scores) / len(scores), 2) if scores else None


@dataclass
class ExamReport:
    exam_date: str
    region: str
    school_code: str
    school_name: str
    subject_codes: List[str]
    students: List[Student]


def _subject_name(code: str) -> str:
    return CBSE_SUBJECT_CODES.get(code, "Subject " + code)


def _parse_marks(line: str, subject_codes: List[str]) -> Tuple[Dict[str, Optional[int]], Dict[str, str]]:
    pairs = re.findall(
        r"\b(\d{1,3}|ABS|AB)\b(?:\s+(A[12]|B[12]|C[12]|D[12]|E[12]?))?",
        line,
    )
    marks: Dict[str, Optional[int]] = {}
    grades: Dict[str, str] = {}
    for code, (mark_text, grade) in zip(subject_codes, pairs):
        marks[code] = int(mark_text) if mark_text.isdigit() else None
        grades[code] = grade or ("AB" if not mark_text.isdigit() else "")
    return marks, grades


def parse_cbse_gazette(text: str) -> ExamReport:
    """Parse a CBSE school/roll-number-wise Gazette text export."""
    date_match = re.search(r"DATE:-\s*(\S+)", text)
    region_match = re.search(r"REGION:\s*([A-Z0-9-]+)", text)
    school_match = re.search(r"SCHOOL\s*:\s*-\s*(\d+)\s+([^\r\n]+)", text)

    students: List[Student] = []
    subject_codes = set()
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = STUDENT_LINE_PATTERN.match(lines[index])
        if not match:
            index += 1
            continue

        roll_no, _, gender, name, codes_text, result_text = match.groups()
        codes = re.findall(r"\d{3}", codes_text)
        subject_codes.update(codes)
        tail = result_text.split()
        internal_grades: List[str] = []
        if len(tail) >= 4 and all(GRADE_PATTERN.match(token) for token in tail[:3]):
            internal_grades = tail[:3]
            tail = tail[3:]

        result = tail[0] if tail else ""
        compartment_subject = " ".join(tail[1:])
        marks_line = lines[index + 1] if index + 1 < len(lines) else ""
        marks, grades = _parse_marks(marks_line, codes)
        students.append(
            Student(
                roll_no=roll_no,
                name=re.sub(r"\s+", " ", name.strip()),
                gender=gender,
                result=result,
                compartment_subject=compartment_subject,
                internal_grades=internal_grades,
                subject_codes=codes,
                marks=marks,
                grades=grades,
            )
        )
        index += 2

    ordered_codes = sorted(
        subject_codes,
        key=lambda code: (0 if code in ("301", "302", "001", "002") else 1, code),
    )
    return ExamReport(
        exam_date=date_match.group(1) if date_match else "",
        region=region_match.group(1) if region_match else "",
        school_code=school_match.group(1).strip() if school_match else "",
        school_name=school_match.group(2).strip() if school_match else "",
        subject_codes=ordered_codes,
        students=students,
    )


def build_subject_analysis(report: ExamReport) -> List[dict]:
    analysis = []
    for code in report.subject_codes:
        enrolled = [student for student in report.students if code in student.subject_codes]
        scored = [student.marks.get(code) for student in enrolled]
        scores = [score for score in scored if score is not None]
        grade_counts = Counter(
            student.grades.get(code, "")
            for student in enrolled
            if student.grades.get(code, "")
        )
        graded = sum(grade_counts.values())
        passes = sum(
            count
            for grade, count in grade_counts.items()
            if grade not in ("E", "E1", "E2", "AB")
        )
        row = {
            "Subject_Code": code,
            "Subject_Name": _subject_name(code),
            "Students_Enrolled": len(enrolled),
            "Students_Appeared": len(scores),
            "Mean_Marks": round(sum(scores) / len(scores), 2) if scores else None,
            "Median_Marks": _median(scores),
            "Highest_Marks": max(scores) if scores else None,
            "Lowest_Marks": min(scores) if scores else None,
            "Pass_Count": passes,
            "Graded_Students": graded,
            "Pass_Percentage": round(100 * passes / graded, 2) if graded else None,
        }
        row.update({"Grade_" + grade: grade_counts.get(grade, 0) for grade in GRADE_ORDER})
        analysis.append(row)
    return analysis


def _median(values: List[int]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return round((ordered[middle - 1] + ordered[middle]) / 2, 1)


def build_student_rows(report: ExamReport) -> List[dict]:
    """Flatten parsed results for display and CSV export."""
    rows = []
    for student in report.students:
        row = {
            "School_Code": report.school_code,
            "School_Name": report.school_name,
            "Region": report.region,
            "Exam_Date": report.exam_date,
            "Roll_No": student.roll_no,
            "Candidate_Name": student.name,
            "Gender": student.gender,
            "Result": student.result,
            "Compartment_Sub": student.compartment_subject,
        }
        for code in report.subject_codes:
            prefix = str(code) + "_" + _subject_name(code).replace(" ", "_")
            row[prefix + "_Marks"] = student.marks.get(code)
            row[prefix + "_Grade"] = student.grades.get(code, "")
        row.update(
            {
                "Total_Marks_All": student.total_marks,
                "Percentage_All": student.percentage_all,
                "Best5_Total_500": student.best_five_marks,
                "Best5_Percentage": student.best_five_percentage,
            }
        )
        rows.append(row)

    ranked = sorted(
        (
            (row["Best5_Percentage"], row["Total_Marks_All"], index)
            for index, row in enumerate(rows)
            if row["Best5_Percentage"] is not None
        ),
        key=lambda item: (-item[0], -(item[1] or 0)),
    )
    rank_by_index: Dict[int, int] = {}
    previous_score = None
    current_rank = 0
    for position, (score, _, index) in enumerate(ranked, start=1):
        if score != previous_score:
            current_rank = position
            previous_score = score
        rank_by_index[index] = current_rank
    for index, row in enumerate(rows):
        row["Rank_Best5"] = rank_by_index.get(index)
    return rows


def performance_bands(report: ExamReport) -> Dict[str, int]:
    labels = [
        "Below 50%",
        "50%–59.9%",
        "60%–74.9%",
        "75%–89.9%",
        "90% and above",
    ]
    counts = dict.fromkeys(labels, 0)
    for student in report.students:
        if student.result.upper() != "PASS" or student.best_five_percentage is None:
            continue
        score = student.best_five_percentage
        if score < 50:
            counts[labels[0]] += 1
        elif score < 60:
            counts[labels[1]] += 1
        elif score < 75:
            counts[labels[2]] += 1
        elif score < 90:
            counts[labels[3]] += 1
        else:
            counts[labels[4]] += 1
    return counts


def answer_question(report: ExamReport, question: str) -> dict:
    """Answer common result-analysis questions from the parsed file, offline."""
    query = re.sub(r"\s+", " ", question.strip().lower())
    if not query:
        return {"message": "Enter a question to get an analysis."}

    roll_match = re.search(r"\b\d{8}\b", query)
    candidate_matches = []
    if roll_match:
        candidate_matches = [
            student for student in report.students if student.roll_no == roll_match.group()
        ]
    else:
        candidate_matches = [
            student
            for student in report.students
            if student.name.lower() in query and len(student.name) > 1
        ]
    if candidate_matches:
        if len(candidate_matches) > 1:
            return {
                "message": "More than one candidate matched. Try a roll number.",
                "students": candidate_matches,
            }
        student = candidate_matches[0]
        return {
            "message": (
                f"{student.name} ({student.roll_no}) — {student.result or 'result unavailable'}; "
                f"best-five score: {student.best_five_percentage:.2f}%"
                if student.best_five_percentage is not None
                else f"{student.name} ({student.roll_no}) — {student.result or 'result unavailable'}; "
                "fewer than five numeric subject marks are available."
            ),
            "students": candidate_matches,
        }

    subject_analysis = build_subject_analysis(report)
    matching_subject = next(
        (
            row
            for row in subject_analysis
            if row["Subject_Code"].lower() in query
            or row["Subject_Name"].lower() in query
            or row["Subject_Name"].lower().replace(" ", "") in query.replace(" ", "")
        ),
        None,
    )
    if matching_subject and any(
        word in query
        for word in (
            "grade",
            "distribution",
            "average",
            "mean",
            "highest",
            "lowest",
            "pass",
            "score",
            "marks",
            "performance",
        )
    ):
        return {
            "message": f"Subject analysis for {matching_subject['Subject_Name']}.",
            "subject": matching_subject,
        }

    if any(word in query for word in ("grade", "distribution", "grades")):
        grade_counts = Counter()
        for student in report.students:
            grade_counts.update(
                grade for grade in student.grades.values() if grade
            )
        return {
            "message": "Grade counts across all recorded subjects.",
            "grades": {grade: grade_counts.get(grade, 0) for grade in GRADE_ORDER},
        }

    if any(word in query for word in ("band", "bands", "distinction", "performance range")):
        return {"message": "Passed candidates grouped by best-five percentage.", "bands": performance_bands(report)}

    if any(word in query for word in ("pass", "result", "compartment", "repeat", "withheld")):
        result_counts = Counter(student.result or "Not stated" for student in report.students)
        passed = result_counts.get("PASS", 0)
        total = len(report.students)
        return {
            "message": f"{passed} of {total} candidates passed ({100 * passed / total:.1f}%).",
            "results": dict(result_counts),
        }

    if any(
        phrase in query
        for phrase in ("top", "performer", "rank", "highest score", "highest marks", "best student")
    ):
        top_students = sorted(
            (
                student
                for student in report.students
                if student.result.upper() == "PASS"
                and student.best_five_percentage is not None
            ),
            key=lambda student: (student.best_five_percentage, student.total_marks or 0),
            reverse=True,
        )[:5]
        return {"message": "Top five passed candidates by best-five percentage.", "students": top_students}

    if any(word in query for word in ("subject", "strongest", "weakest", "best", "worst", "average")):
        ranked = sorted(
            (row for row in subject_analysis if row["Mean_Marks"] is not None),
            key=lambda row: row["Mean_Marks"],
        )
        if ranked:
            if any(word in query for word in ("weakest", "lowest", "worst")):
                selected = ranked[:3]
                description = "Lowest subject averages."
            else:
                selected = list(reversed(ranked[-3:]))
                description = "Highest subject averages."
            return {"message": description, "subjects": selected}

    return {
        "message": (
            "I can answer questions about a candidate (name or roll number), subject "
            "averages/grades/pass rates, grade distribution, result breakdown, "
            "performance bands, or top performers."
        )
    }
