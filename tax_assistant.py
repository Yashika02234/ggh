import warnings
warnings.filterwarnings("ignore", category=UserWarning)
pip install scikit-learn
import streamlit as st
import json
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import time

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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

# Show login form if not logged in
if not st.session_state.logged_in:
    st.title("📊 TaxMate- Login")

    # Wrap the login form in a st.form
    with st.form("login_form"):
        # Input fields for username and password
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        # Login button
        if st.form_submit_button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()  # Rerun the app to show the main interface
            else:
                st.error("Invalid username or password")
else:
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
        
        # Convert input data to a DataFrame with feature names
        input_data = pd.DataFrame({
            "income": [user_data["income"]],
            "medical_expenses": [user_data["medical_expenses"]],
            "charity": [user_data["charity"]]
        })
        
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

    # Function to generate tax savings tips
    def generate_tax_savings_tips(user_data, tax_rules):
        """
        Generates tax savings tips based on user data and tax rules.
        
        Args:
            user_data (dict): Dictionary containing user inputs (income, medical_expenses, charity, etc.).
            tax_rules (dict): Dictionary containing tax rules (standard deduction, itemized deductions, etc.).
        
        Returns:
            list: List of tax savings tips.
        """
        tips = []
        
        # Tip 1: Retirement contributions
        retirement_limit = tax_rules["itemized_deductions"]["retirement_contributions"]["limit"]
        if user_data["retirement_contributions"] < retirement_limit:
            tips.append(f"Consider increasing your retirement contributions to maximize deductions (up to ${retirement_limit:,.2f}).")
        
        # Tip 2: Medical expenses
        medical_threshold = tax_rules["itemized_deductions"]["medical_expenses"]["threshold"]
        if user_data["medical_expenses"] > user_data["income"] * medical_threshold:
            tips.append("You may be eligible to deduct medical expenses. Keep track of all receipts.")
        
        # Tip 3: Charity donations
        charity_limit = tax_rules["itemized_deductions"]["charity"]["limit"]
        if user_data["charity"] < user_data["income"] * charity_limit:
            tips.append(f"Consider increasing your charitable donations to maximize deductions (up to {charity_limit * 100}% of your income).")
        
        # Tip 4: Student loan interest
        if "student_loan_interest" in user_data and user_data["student_loan_interest"] > 0:
            tips.append("You can deduct up to $2,500 of student loan interest paid.")
        
        # Tip 5: Home office deduction
        if "home_office" in user_data and user_data["home_office"] > 0:
            tips.append("You may be eligible for a home office deduction. Ensure you meet the requirements.")
        
        return tips

    # Streamlit UI
    st.title("📊 TaxMate")

    # Sidebar for year selection
    st.sidebar.header("Options")
    year = st.sidebar.selectbox("Select Tax Year", list(tax_rules.keys()))
    tax_rules = tax_rules[year]

    # Tabs for better navigation
    tab1, tab2, tab3, tab4 = st.tabs(["Inputs", "Results", "Visualizations", "Tax Savings Tips"])

    with tab1:
        st.subheader("📝 Inputs")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 💰 Income and Expenses")
            income = st.number_input("Enter your income", min_value=0, help="Your total annual income before deductions.")
            medical_expenses = st.number_input("Enter medical expenses", min_value=0, help="Medical expenses exceeding 7.5% of your income.")
            charity = st.number_input("Enter charity donations", min_value=0, help="Donations to qualified charities.")

        with col2:
            st.markdown("### 📉 Deductions")
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
    if income > 0 or medical_expenses > 0 or charity > 0 or student_loan_interest > 0 or home_office > 0 or retirement_contributions > 0:
        with st.spinner("Calculating..."):
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)  # Simulate calculation time
                progress_bar.progress(i + 1)
            deductions = identify_deductions(user_data, tax_rules)
            taxable_income = calculate_taxable_income(income, deductions)
            tax = calculate_tax(taxable_income, tax_rules)
    else:
        deductions = 0
        taxable_income = 0
        tax = 0

    with tab2:
        st.subheader("📊 Results")
        
        # Check if inputs are provided
        if income == 0 and medical_expenses == 0 and charity == 0 and student_loan_interest == 0 and home_office == 0 and retirement_contributions == 0:
            st.warning("Please enter your financial data in the Inputs tab to see results.")
        else:
            # Display results using st.metric for better UI
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Taxable Income", f"${taxable_income:,.2f}")
            with col2:
                st.metric("Tax Owed", f"${tax:,.2f}")
            with col3:
                st.metric("Total Deductions", f"${deductions:,.2f}")

            # Predict optimal deductions
            optimal_deductions = predict_optimal_deductions(user_data)
            st.write(f"**Optimal Deductions (Predicted):** ${optimal_deductions:,.2f}")

            # Save data
            if st.button("💾 Save Data"):
                save_user_data(user_data, taxable_income, tax, deductions)
                st.success("Data saved successfully!")

    with tab3:
        st.subheader("📈 Visualizations")
        
        # Check if inputs are provided
        if income == 0 and medical_expenses == 0 and charity == 0 and student_loan_interest == 0 and home_office == 0 and retirement_contributions == 0:
            st.warning("Please enter your financial data in the Inputs tab to see visualizations.")
        else:
            # Visualization: Pie chart
            st.markdown("### 🥧 Tax Breakdown")
            labels = ["Tax Owed", "Deductions", "Net Income"]
            values = [tax, deductions, income - tax]
            colors = ["#ff9999", "#66b3ff", "#99ff99"]  # Custom colors for the pie chart
            
            fig, ax = plt.subplots()
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors, explode=(0.1, 0, 0))
            ax.axis("equal")  # Equal aspect ratio ensures the pie chart is circular.
            
            # Display the pie chart
            st.pyplot(fig)

            # Add a description for the pie chart
            st.write("""
            - **Tax Owed**: The amount of tax you need to pay.
            - **Deductions**: The total deductions applied to your income.
            - **Net Income**: Your income after tax and deductions.
            """)

    with tab4:
        st.subheader("💡 Tax Savings Tips")
        
        # Generate and display tips
        tips = generate_tax_savings_tips(user_data, tax_rules)
        if tips:
            st.write("Here are some tips to help you save on taxes:")
            for tip in tips:
                st.write(f"- {tip}")
        else:
            st.write("No specific tax savings tips available based on your data.")
        
        # Add links to external resources
        st.markdown("### 📚 Helpful Resources")
        st.write("For more information, check out these resources:")
        st.write("- [IRS Official Website](https://www.irs.gov/)")
        st.write("- [Investopedia Tax Guide](https://www.investopedia.com/taxes-4769804)")
        st.write("- [TurboTax Tax Tips](https://turbotax.intuit.com/)")

    # Export results
    st.sidebar.header("Export")
    if st.sidebar.button("📄 Export as PDF"):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf = canvas.Canvas("tax_results.pdf", pagesize=letter)
        pdf.drawString(100, 750, "Tax Results")
        pdf.drawString(100, 730, f"Taxable Income: ${taxable_income:,.2f}")
        pdf.drawString(100, 710, f"Tax Owed: ${tax:,.2f}")
        pdf.drawString(100, 690, f"Deductions: ${deductions:,.2f}")
        pdf.save()
        st.sidebar.success("Exported as PDF!")

    if st.sidebar.button("📝 Export as CSV"):
        data = {
            "Taxable Income": [taxable_income],
            "Tax Owed": [tax],
            "Deductions": [deductions]
        }
        df = pd.DataFrame(data)
        df.to_csv("tax_results.csv", index=False)
        st.sidebar.success("Exported as CSV!")