import json
import streamlit as st

# Load tax rules
with open("tax_rules.json", "r") as file:
    tax_rules = json.load(file)

# Function to calculate taxable income
def calculate_taxable_income(income, deductions):
    return max(0, income - deductions)

# Function to calculate tax
def calculate_tax(taxable_income, tax_rules):
    tax = 0
    for bracket in tax_rules["tax_brackets"]:
        if taxable_income > bracket["min"]:
            taxable_amount = min(taxable_income, bracket["max"] or float('inf')) - bracket["min"]
            tax += taxable_amount * bracket["rate"]
    return tax

# Function to identify deductions
def identify_deductions(user_data, tax_rules):
    deductions = tax_rules["standard_deduction"]
    if user_data["medical_expenses"] > user_data["income"] * tax_rules["itemized_deductions"]["medical_expenses"]["threshold"]:
        deductions += user_data["medical_expenses"]
    if user_data["charity"] > 0:
        deductions += min(user_data["charity"], user_data["income"] * tax_rules["itemized_deductions"]["charity"]["limit"])
    return deductions

# Streamlit UI
st.title("Tax Assistant")
income = st.number_input("Enter your income", min_value=0)
medical_expenses = st.number_input("Enter medical expenses", min_value=0)
charity = st.number_input("Enter charity donations", min_value=0)

user_data = {"income": income, "medical_expenses": medical_expenses, "charity": charity}
deductions = identify_deductions(user_data, tax_rules)
taxable_income = calculate_taxable_income(income, deductions)
tax = calculate_tax(taxable_income, tax_rules)

st.write(f"Taxable Income: {taxable_income}")
st.write(f"Tax Owed: {tax}")