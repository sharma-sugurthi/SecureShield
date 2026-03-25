#!/usr/bin/env python3
"""
Generate realistic sample insurance policy PDFs for SecureShield E2E testing.
Creates 2 policies with different coverage levels and rules.
"""

from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


class PolicyPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, self.title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(230, 240, 250)
        self.cell(0, 9, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"    - {text}", new_x="LMARGIN", new_y="NEXT")

    def key_value(self, key, val):
        self.set_font("Helvetica", "B", 10)
        self.cell(70, 7, key)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 7, val, new_x="LMARGIN", new_y="NEXT")

    def add_table(self, headers, rows):
        col_w = (self.w - 20) / len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(41, 58, 74)
        self.set_text_color(255, 255, 255)
        for h in headers:
            self.cell(col_w, 8, h, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        for row in rows:
            for val in row:
                self.cell(col_w, 7, str(val), border=1, align="C")
            self.ln()
        self.ln(4)


def create_policy_1():
    """Star Health — Premier Gold Plan (high coverage, generous limits)"""
    pdf = PolicyPDF()
    pdf.title = "Star Health Premier Gold - Policy Document"
    pdf.alias_nb_pages()
    pdf.add_page()

    # Page 1 — Overview
    pdf.section_title("1. Policy Overview")
    pdf.key_value("Plan Name:", "Star Health Premier Gold")
    pdf.key_value("Policy Number:", "SH-GOLD-2024-78291")
    pdf.key_value("Insurer:", "Star Health and Allied Insurance Co. Ltd.")
    pdf.key_value("Effective Date:", "01-Apr-2024 to 31-Mar-2025")
    pdf.key_value("Sum Insured:", "Rs. 10,00,000 (Ten Lakhs)")
    pdf.key_value("Policyholder:", "Sample Policyholder")
    pdf.key_value("Coverage Type:", "Individual Floater")
    pdf.ln(4)

    pdf.section_title("2. Coverage Details")
    pdf.body_text(
        "This policy provides comprehensive health insurance coverage including "
        "hospitalization, pre and post hospitalization expenses, day care procedures, "
        "and ambulance charges as per the terms and conditions mentioned below."
    )

    pdf.section_title("3. Room Rent Eligibility")
    pdf.body_text(
        "The policyholder is entitled to room rent as per the following limits:"
    )
    pdf.add_table(
        ["Room Category", "Maximum Per Day (Rs.)", "Condition"],
        [
            ["General Ward", "No Limit", "Covered in full"],
            ["Semi-Private", "5,000", "Subject to proportional deduction"],
            ["Private Room", "8,000", "Subject to proportional deduction"],
            ["Single AC", "10,000", "Subject to proportional deduction"],
            ["Deluxe / Suite", "Not Covered", "Upgrade at own expense"],
            ["ICU", "15,000", "Max 10 days per hospitalization"],
        ],
    )

    pdf.section_title("4. Pre-Existing Disease (PED) Clause")
    pdf.body_text(
        "Pre-existing diseases are covered after a continuous waiting period of "
        "48 months (4 years) from the date of inception of the first policy. "
        "Diseases diagnosed within 48 months prior to the policy start date are "
        "classified as pre-existing and will not be covered during the waiting period."
    )
    pdf.body_text(
        "Conditions covered after waiting period include: Diabetes Mellitus, "
        "Hypertension, Thyroid disorders, Asthma, and Cardiac conditions."
    )

    # Page 2
    pdf.add_page()
    pdf.section_title("5. Waiting Period for Specific Procedures")
    pdf.add_table(
        ["Procedure", "Waiting Period", "Remarks"],
        [
            ["Cataract Surgery", "24 months", "Max Rs. 50,000 per eye"],
            ["Joint Replacement", "24 months", "Covered after waiting period"],
            ["Hernia Repair", "24 months", "Covered after waiting period"],
            ["Kidney Stone (Lithotripsy)", "12 months", "Covered after waiting period"],
            ["Appendectomy", "No waiting", "Covered from day 1"],
            ["CABG / Bypass Surgery", "No waiting", "Emergency: covered from day 1"],
            ["Angioplasty (PTCA)", "No waiting", "Emergency: covered from day 1"],
        ],
    )

    pdf.section_title("6. Exclusions")
    pdf.bullet("Cosmetic or aesthetic treatments")
    pdf.bullet("Self-inflicted injuries or substance abuse related treatment")
    pdf.bullet("Dental treatment unless arising from accident")
    pdf.bullet("Obesity / weight management surgery (BMI < 40)")
    pdf.bullet("Experimental or unproven treatments")
    pdf.bullet("War, nuclear contamination related injuries")
    pdf.bullet("Maternity benefits (separate rider required)")
    pdf.ln(4)

    pdf.section_title("7. Co-Payment Clause")
    pdf.body_text(
        "A co-payment of 10% shall be applicable for policyholders aged 60 years "
        "and above. No co-payment for policyholders below 60 years of age."
    )

    pdf.section_title("8. Claim Limits by Category")
    pdf.add_table(
        ["Category", "Sub-Limit", "Maximum (Rs.)"],
        [
            ["Hospitalization", "No sub-limit", "10,00,000"],
            ["ICU Charges", "Per day cap", "15,000/day"],
            ["Ambulance", "Per incident", "3,000"],
            ["Pre-hospitalization", "30 days before", "Up to 15% of claim"],
            ["Post-hospitalization", "60 days after", "Up to 10% of claim"],
            ["Day Care Procedures", "No sub-limit", "10,00,000"],
        ],
    )

    pdf.section_title("9. Network Hospitals")
    pdf.body_text(
        "Cashless facility is available at 10,000+ network hospitals across India. "
        "For non-network hospitals, reimbursement will be processed within 30 days."
    )

    pdf.section_title("10. IRDAI Compliance")
    pdf.body_text(
        "This policy is issued in compliance with IRDAI (Health Insurance) Regulations, 2016 "
        "and all subsequent amendments. Grievance redressal as per IRDAI circular "
        "IRDA/HLT/REG/CIR/2020. Policy is portable under IRDAI portability guidelines."
    )

    path = os.path.join(OUTPUT_DIR, "star_health_premier_gold.pdf")
    pdf.output(path)
    print(f"Created: {path}")
    return path


def create_policy_2():
    """ICICI Lombard — Basic Shield Plan (lower coverage, stricter limits)"""
    pdf = PolicyPDF()
    pdf.title = "ICICI Lombard Basic Shield - Policy Document"
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.section_title("1. Policy Overview")
    pdf.key_value("Plan Name:", "ICICI Lombard Basic Shield")
    pdf.key_value("Policy Number:", "IL-BASIC-2024-45102")
    pdf.key_value("Insurer:", "ICICI Lombard General Insurance Co. Ltd.")
    pdf.key_value("Effective Date:", "15-Jun-2024 to 14-Jun-2025")
    pdf.key_value("Sum Insured:", "Rs. 3,00,000 (Three Lakhs)")
    pdf.key_value("Policyholder:", "Sample Policyholder")
    pdf.key_value("Coverage Type:", "Individual")
    pdf.ln(4)

    pdf.section_title("2. Coverage Details")
    pdf.body_text(
        "This is an affordable basic health insurance plan designed for individuals "
        "seeking essential hospitalization coverage. Benefits are subject to the "
        "sub-limits and conditions specified in this document."
    )

    pdf.section_title("3. Room Rent Eligibility")
    pdf.body_text("Room rent is limited based on the category selected during admission:")
    pdf.add_table(
        ["Room Category", "Maximum Per Day (Rs.)", "Condition"],
        [
            ["General Ward", "1,500", "Covered"],
            ["Semi-Private", "3,000", "Proportional deduction applies"],
            ["Private Room", "Not Covered", "Upgrade at own expense"],
            ["ICU", "6,000", "Max 5 days per hospitalization"],
        ],
    )

    pdf.section_title("4. Pre-Existing Disease (PED) Clause")
    pdf.body_text(
        "Pre-existing diseases are covered only after a continuous waiting period of "
        "48 months (4 years). Conditions diagnosed within this period are excluded. "
        "Common PEDs include: Diabetes, Hypertension, Kidney disease, Heart disease."
    )

    pdf.section_title("5. Waiting Period for Specific Procedures")
    pdf.add_table(
        ["Procedure", "Waiting Period"],
        [
            ["Cataract Surgery", "24 months"],
            ["Joint Replacement", "36 months"],
            ["Hernia Repair", "24 months"],
            ["Appendectomy", "30 days"],
            ["Knee Arthroscopy", "24 months"],
        ],
    )

    pdf.add_page()
    pdf.section_title("6. Exclusions")
    pdf.bullet("Cosmetic and dental procedures (non-accidental)")
    pdf.bullet("Obesity surgery")
    pdf.bullet("Self-inflicted injuries")
    pdf.bullet("Alternative medicine (Ayurveda, Homeopathy)")
    pdf.bullet("Hearing aids, spectacles, contact lenses")
    pdf.bullet("Maternity and newborn expenses")
    pdf.bullet("Congenital conditions")
    pdf.ln(4)

    pdf.section_title("7. Co-Payment Clause")
    pdf.body_text(
        "A mandatory co-payment of 20% shall apply to all claims. "
        "For policyholders aged 55 and above, the co-payment increases to 30%."
    )

    pdf.section_title("8. Claim Limits")
    pdf.add_table(
        ["Category", "Sub-Limit", "Maximum (Rs.)"],
        [
            ["Hospitalization", "1% of SI per day", "3,00,000"],
            ["ICU Charges", "Per day cap", "6,000/day"],
            ["Ambulance", "Per incident", "1,500"],
            ["Pre-hospitalization", "15 days before", "Up to 10% of claim"],
            ["Post-hospitalization", "30 days after", "Up to 5% of claim"],
        ],
    )

    pdf.section_title("9. IRDAI Compliance")
    pdf.body_text(
        "This policy complies with IRDAI (Health Insurance) Regulations, 2016. "
        "All terms and conditions are subject to IRDAI guidelines."
    )

    path = os.path.join(OUTPUT_DIR, "icici_lombard_basic_shield.pdf")
    pdf.output(path)
    print(f"Created: {path}")
    return path


if __name__ == "__main__":
    print("Generating sample insurance policy PDFs...\n")
    create_policy_1()
    create_policy_2()
    print("\nDone! PDFs ready for upload testing.")
