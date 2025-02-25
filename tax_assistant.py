import streamlit as st
import json
import matplotlib.pyplot as plt

# Load tax rules
with open("tax_rules.json", "r") as file:
    tax_rules = json.load(file)

# Function to calculate taxable income
def calculate_taxable_income(income, deductions):
    """
    Calculate taxable income by subtracting deductions from total income.
    
    Args:
        income (float): Total income.
        deductions (float): Total deductions.
    
    Returns:
        float: Taxable income.
    """
    return max(0, income - deductions)

# Function to calculate tax
def calculate_tax(taxable_income, tax_rules):
    tax = 0
    for bracket in tax_rules["tax_brackets"]:
        if taxable_income > bracket["min"]:
            taxable_amount = min(taxable_income, bracket["max"] or float('inf')) - bracket["min"]
            tax += taxable_amount * bracket["rate"]
        else:
            break  # No need to continue once taxable income is lower than min of next bracket
    return round(tax, 2)

# Function to identify deductions
def identify_deductions(user_data, tax_rules):
    """
    Calculate total deductions based on user inputs and tax rules.
    
    Args:
        user_data (dict): Dictionary containing user inputs (income, medical_expenses, charity, etc.).
        tax_rules (dict): Dictionary containing tax rules (standard deduction, itemized deductions, etc.).
    
    Returns:
        float: Total deductions.
    """
    # Start with the standard deduction
    deductions = tax_rules["standard_deduction"]
    
    # Medical expenses deduction
    medical_threshold = tax_rules["itemized_deductions"]["medical_expenses"]["threshold"]
    if user_data["medical_expenses"] > user_data["income"] * medical_threshold:
        deductions += user_data["medical_expenses"] - (user_data["income"] * medical_threshold)
    
    # Charity deduction
    charity_limit = tax_rules["itemized_deductions"]["charity"]["limit"]
    if user_data["charity"] > 0:
        deductions += min(user_data["charity"], user_data["income"] * charity_limit)
    
    # Student loan interest deduction
    if "student_loan_interest" in user_data and user_data["student_loan_interest"] > 0:
        student_loan_limit = tax_rules["itemized_deductions"]["student_loan_interest"]["limit"]
        deductions += min(user_data["student_loan_interest"], student_loan_limit)
    
    # Home office deduction
    if "home_office" in user_data and user_data["home_office"] > 0:
        home_office_deduction = min(user_data["home_office"] * tax_rules["itemized_deductions"]["home_office"]["rate"], tax_rules["itemized_deductions"]["home_office"]["max_limit"])
        deductions += home_office_deduction
    
    # Retirement contributions deduction
    if "retirement_contributions" in user_data and user_data["retirement_contributions"] > 0:
        retirement_limit = tax_rules["itemized_deductions"]["retirement_contributions"]["limit"]
        deductions += min(user_data["retirement_contributions"], retirement_limit)
    
    return deductions

# Streamlit UI
st.title("Tax Assistant")

# Input fields
income = st.number_input("Enter your income", min_value=0, help="Your total annual income before deductions.")
medical_expenses = st.number_input("Enter medical expenses", min_value=0, help="Medical expenses exceeding 7.5% of your income.")
charity = st.number_input("Enter charity donations", min_value=0, help="Donations to qualified charities.")
student_loan_interest = st.number_input("Enter student loan interest paid", min_value=0, help="Interest paid on student loans (up to $2,500).")
home_office = st.number_input("Enter home office expenses", min_value=0, help="Expenses for a home office (up to $1,500).")
retirement_contributions = st.number_input("Enter retirement contributions", min_value=0, help="Contributions to retirement accounts (up to $6,000).")

# Prepare user data
user_data = {
    "income": income,
    "medical_expenses": medical_expenses,
    "charity": charity,
    "student_loan_interest": student_loan_interest,
    "home_office": home_office,
    "retirement_contributions": retirement_contributions
}

# Calculate deductions, taxable income, and tax
deductions = identify_deductions(user_data, tax_rules)
taxable_income = calculate_taxable_income(income, deductions)
tax = calculate_tax(taxable_income, tax_rules)

# Display results
st.subheader("Results")
st.write(f"**Taxable Income:** ${taxable_income:,.2f}")
st.write(f"**Tax Owed:** ${tax:,.2f}")
st.write(f"**Total Deductions:** ${deductions:,.2f}")

# Visualization: Pie chart
st.subheader("Tax Breakdown")
labels = ["Tax Owed", "Deductions", "Net Income"]
values = [tax, deductions, income - tax]
fig, ax = plt.subplots()
ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
ax.axis("equal")  # Equal aspect ratio ensures the pie chart is circular.
st.pyplot(fig)

# Export results
if st.button("Export as PDF"):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas("tax_results.pdf", pagesize=letter)
    pdf.drawString(100, 750, "Tax Results")
    pdf.drawString(100, 730, f"Taxable Income: ${taxable_income:,.2f}")
    pdf.drawString(100, 710, f"Tax Owed: ${tax:,.2f}")
    pdf.drawString(100, 690, f"Deductions: ${deductions:,.2f}")
    pdf.save()
    st.success("Exported as PDF!")

if st.button("Export as CSV"):
    import pandas as pd
    data = {
        "Taxable Income": [taxable_income],
        "Tax Owed": [tax],
        "Deductions": [deductions]
    }
    df = pd.DataFrame(data)
    df.to_csv("tax_results.csv", index=False)
    st.success("Exported as CSV!")