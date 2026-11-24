import unittest
from pathlib import Path

from exam_analysis import (
    answer_question,
    build_subject_analysis,
    build_student_rows,
    parse_cbse_gazette,
    performance_bands,
)


GAZETTE = """DATE:- 15/04/2025 DEMONSTRATION EXAM REGION: SAMPLE-REGION
SCHOOL : - 99999 DEMONSTRATION ACADEMY
ROLL    F S NAME OF CANDIDATE
90000001   M DEMO STUDENT ONE             301     002     028     029     030      A1 A1 A1 PASS
                                            099 A1 080 A2 070 B1 060 C1 050 D1
90000002   F DEMO STUDENT TWO             301     002     028     029     030      R.L.

TOTAL CANDIDATES : 2
"""


class ExamAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.report = parse_cbse_gazette(GAZETTE)

    def test_parses_metadata_students_marks_and_withheld_result(self):
        self.assertEqual(self.report.exam_date, "15/04/2025")
        self.assertEqual(self.report.region, "SAMPLE-REGION")
        self.assertEqual(self.report.school_code, "99999")
        self.assertEqual(len(self.report.students), 2)
        first, withheld = self.report.students
        self.assertEqual(first.roll_no, "90000001")
        self.assertEqual(first.name, "DEMO STUDENT ONE")
        self.assertEqual(first.best_five_percentage, 71.8)
        self.assertEqual(first.total_marks, 359)
        self.assertEqual(withheld.roll_no, "90000002")
        self.assertEqual(withheld.result, "R.L.")
        self.assertIsNone(withheld.best_five_percentage)

    def test_subject_statistics_and_export_rank(self):
        rows = build_subject_analysis(self.report)
        english = next(row for row in rows if row["Subject_Code"] == "301")
        self.assertEqual(english["Students_Enrolled"], 2)
        self.assertEqual(english["Students_Appeared"], 1)
        self.assertEqual(english["Grade_A1"], 1)
        self.assertEqual(english["Pass_Percentage"], 100)
        export_rows = build_student_rows(self.report)
        self.assertEqual(export_rows[0]["Rank_Best5"], 1)
        self.assertIsNone(export_rows[1]["Best5_Total_500"])

    def test_question_answers_and_performance_bands(self):
        answer = answer_question(self.report, "What is the average for English Core?")
        self.assertEqual(answer["subject"]["Mean_Marks"], 99)
        self.assertEqual(answer_question(self.report, "result breakdown")["results"]["PASS"], 1)
        best_performer = answer_question(self.report, "Who is the best performer?")
        self.assertEqual(best_performer["students"][0].roll_no, "90000001")
        self.assertEqual(sum(performance_bands(self.report).values()), 1)

    def test_demo_text_file_contains_only_demo_records(self):
        demo_path = Path(__file__).resolve().parents[1] / "demo_data.txt"
        text = demo_path.read_text(encoding="utf-8")
        report = parse_cbse_gazette(text)

        self.assertEqual(report.school_name, "SYNTHETIC DATA ONLY")
        self.assertEqual(report.region, "DEMO-REGION")
        self.assertEqual(len(report.students), 200)
        self.assertEqual(len({student.roll_no for student in report.students}), 200)
        self.assertTrue(
            all(90000001 <= int(student.roll_no) <= 90000200 for student in report.students)
        )
        self.assertTrue(all(student.name.startswith("DEMO CANDIDATE ") for student in report.students))
        self.assertGreaterEqual(len(report.subject_codes), 8)
        self.assertGreater(len({tuple(student.subject_codes) for student in report.students}), 1)
        self.assertTrue(any(student.result == "COMP" for student in report.students))
        self.assertTrue(any(student.result == "R.L." for student in report.students))
        self.assertTrue(
            any(grade == "E" for student in report.students for grade in student.grades.values())
        )


if __name__ == "__main__":
    unittest.main()
