import unittest

from exam_analysis import (
    answer_question,
    build_subject_analysis,
    build_student_rows,
    parse_cbse_gazette,
    performance_bands,
)


GAZETTE = """DATE:- 30/07/2021 C.B.S.E. EXAM REGION: DELHI-EAST
SCHOOL : - 27370 GOVT BOYS SCHOOL
ROLL    F S NAME OF CANDIDATE
12345678   M ARUN KUMAR                  301     002     028     029     030      A1 A1 A1 PASS
                                            099 A1 080 A2 070 B1 060 C1 050 D1
12345679   M DEV                           301     002     028     029     030      R.L.

TOTAL CANDIDATES : 2
"""


class ExamAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.report = parse_cbse_gazette(GAZETTE)

    def test_parses_metadata_students_marks_and_withheld_result(self):
        self.assertEqual(self.report.exam_date, "30/07/2021")
        self.assertEqual(self.report.region, "DELHI-EAST")
        self.assertEqual(self.report.school_code, "27370")
        self.assertEqual(len(self.report.students), 2)
        first, withheld = self.report.students
        self.assertEqual(first.name, "ARUN KUMAR")
        self.assertEqual(first.best_five_percentage, 71.8)
        self.assertEqual(first.total_marks, 359)
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
        self.assertEqual(best_performer["students"][0].roll_no, "12345678")
        self.assertEqual(sum(performance_bands(self.report).values()), 1)


if __name__ == "__main__":
    unittest.main()
