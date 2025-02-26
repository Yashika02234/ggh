import streamlit as st
import json
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Function to check if the user is authenticated
def authenticate(username, password):
    """
    Check if the provided username and password match the secrets.
    
    Args:
        username (str): Username entered by the user.
        password (str): Password entered by the user.
    
    Returns:
        bool: True if authenticated, False otherwise.
    """
    return username == st.secrets["authentication"]["username"] and password == st.secrets["authentication"]["password"]

# Login form
st.title("Tax Assistant - Login")

# Input fields for username and password
username = st.text_input("Username")
password = st.text_input("Password", type="password")

# Login button
if st.button("Login"):
    if authenticate(username, password):
        st.success("Logged in successfully!")

        # Load tax rules
        with open("tax_rules.json", "r") as file:
            tax_rules = json.load(file)

        # Connect to SQLite database
        conn = sqlite3.connect("tax_data.db")
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tax_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                income REAL,
                medical_expenses REAL,
                charity REAL,
                student_loan_interest REAL,
                home_office REAL,
                retirement_contributions REAL,
                taxable_income REAL,
                tax_owed REAL,
                deductions REAL
            )
        """)
        conn.commit()

        # Function to save user data
        def save_user_data(user_data, taxable_income, tax, deductions):
            cursor.execute("""
                INSERT INTO tax_records (
                    year, income, medical_expenses, charity, student_loan_interest,
                    home_office, retirement_contributions, taxable_income, tax_owed, deductions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data["year"], user_data["income"], user_data["medical_expenses"],
                user_data["charity"], user_data["student_loan_interest"],
                user_data["home_office"], user_data["retirement_contributions"],
                taxable_income, tax, deductions
            ))
            conn.commit()

        # Function to predict optimal deductions
        def predict_optimal_deductions(user_data):
            # Example dataset (replace with real data)
            data = {
                "income": [50000, 60000, 70000],
                "medical_expenses": [5000, 6000, 7000],
                "charity": [2000, 3000, 4000],
                "optimal_deductions": [15000, 18000, 21000]
            }
            df = pd.DataFrame(data)
            X = df[["income", "medical_expenses", "charity"]]
            y = df["optimal_deductions"]
            model = LinearRegression()
            model.fit(X, y)
            input_data = [[user_data["income"], user_data["medical_expenses"], user_data["charity"]]]
            return model.predict(input_data)[0]

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

        # Sidebar for year selection
        year = st.sidebar.selectbox("Select Tax Year", list(tax_rules.keys()))
        tax_rules = tax_rules[year]

        # Input fields
        income = st.number_input("Enter your income", min_value=0, help="Your total annual income before deductions.")
        medical_expenses = st.number_input("Enter medical expenses", min_value=0, help="Medical expenses exceeding 7.5% of your income.")
        charity = st.number_input("Enter charity donations", min_value=0, help="Donations to qualified charities.")
        student_loan_interest = st.number_input("Enter student loan interest paid", min_value=0, help="Interest paid on student loans (up to $2,500).")
        home_office = st.number_input("Enter home office expenses", min_value=0, help="Expenses for a home office (up to $1,500).")
        retirement_contributions = st.number_input("Enter retirement contributions", min_value=0, help="Contributions to retirement accounts (up to $6,000).")

        # Prepare user data
        user_data = {
            "year": int(year),
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

        # Predict optimal deductions
        optimal_deductions = predict_optimal_deductions(user_data)
        st.write(f"**Optimal Deductions (Predicted):** ${optimal_deductions:,.2f}")

        # Save data
        if st.button("Save Data"):
            save_user_data(user_data, taxable_income, tax, deductions)
            st.success("Data saved successfully!")

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
            data = {
                "Taxable Income": [taxable_income],
                "Tax Owed": [tax],
                "Deductions": [deductions]
            }
            df = pd.DataFrame(data)
            df.to_csv("tax_results.csv", index=False)
            st.success("Exported as CSV!")
    else:
        st.error("Invalid username or password")