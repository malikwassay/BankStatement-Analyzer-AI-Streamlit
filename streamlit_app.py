import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import re


# Page configuration
st.set_page_config(
    page_title="Bank Statement Analysis",
    page_icon="🏦",
    layout="wide"
)

# API endpoint
API_ENDPOINT = "http://15.185.99.179:3000/analyze"

def format_currency(value):
    """Format currency values to 2 decimal places"""
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    elif isinstance(value, str):
        try:
            # Try to convert string to float and format
            num_value = float(value.replace(',', ''))
            return f"{num_value:.2f}"
        except (ValueError, TypeError):
            return value
    return value

def format_text_with_currency(text):
    """Format text that contains currency values to 2 decimal places"""
    if not isinstance(text, str):
        return text
    
    # Find and replace decimal numbers with many places
    pattern = r'(\d+\.\d{3,})'  # Matches numbers with 3 or more decimal places
    
    def replace_func(match):
        try:
            number = float(match.group(1))
            return f"{number:.2f}"
        except ValueError:
            return match.group(1)
    
    return re.sub(pattern, replace_func, text)

def make_api_request_with_files(data, statement_file=None, supporting_file=None):
    """Make POST request to the Flask API with file uploads"""
    try:
        files = {}
        if statement_file is not None:
            files['statement_file'] = ('statement.pdf', statement_file.getvalue(), 'application/pdf')
        if supporting_file is not None:
            files['supporting_file'] = ('supporting.pdf', supporting_file.getvalue(), 'application/pdf')
        
        response = requests.post(API_ENDPOINT, data=data, files=files, timeout=3000)
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}, 500

def make_api_request_with_urls(data):
    """Make POST request to the Flask API with URLs only"""
    try:
        response = requests.post(API_ENDPOINT, json=data, timeout=3000)
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}, 500

def get_friendly_field_name(field_name):
    """Convert camelCase field names to user-friendly titles"""
    field_mapping = {
        # UK fields
        "boundAmountDependant_PKR": "Living Expense Of Dependent In PKR",
        "boundAmountStudent_PKR": "Living Expense of Student In PKR",
        "dependant": "Dependant",
        "exchangeRateGBP": "Exchange Rate GBP After Addition",
        "locationStatus": "Location Status",
        "tuitionFees_PKR": "Tuition Fees In PKR",
        "universityName": "University Name",
        "exchangeRateGBPOriginal": "Exchange Rate GBP Original From OANDA",
        
        # Australia fields
        "exchangeRateAUS": "Exchange Rate AUD After Addition",
        "exchangeRateAUSOriginal": "Exchange Rate AUD Original From OANDA",
        "durationToCheck": "Duration To Check",
        "livingExpense_PKR": "Living Expense In PKR",
        "oneYearFees_PKR": "One Year Fees In PKR",
        # "totalAmountToCheck": "Total Amount To Check",
        "travelExpense_PKR": "Travel Expense In PKR"
    }
    
    return field_mapping.get(field_name, field_name)

def display_analysis_results(result, exchange_rate_plus=0, location=""):
    """Display the analysis results in a formatted way"""
    if "error" in result:
        st.error(f"Error: {result['error']}")
        return
    
    # Display main information
    if "Information" in result:
        info = result["Information"]
        
        # Verdict with color coding
        verdict = info.get("verdict", "Unknown")
        if verdict == "Original":
            st.success(f"🟢 **Verdict: {verdict}**")
        else:
            st.error(f"🔴 **Verdict: {verdict}**")
        
        # Fund Maintenance Check - Display right after verdict
        if "fundMaintenanceCheck" in info:
            fund_check = info["fundMaintenanceCheck"]
            if fund_check.get("isMaintained", False):
                st.success("**Fund Maintenance: The amount in bank account is sufficient**")
                if "finalSummary" in fund_check:
                    # Format currency values in the summary
                    summary = format_text_with_currency(fund_check["finalSummary"])
                    st.write(summary)
            else:
                st.error("**Fund Maintenance: The amount in bank account is not sufficient**")

        # Exchange Rate section with OANDA source information
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.info(
            "📈 **Exchange Rate Source:** OANDA  \n"
            f"🕐 **Extract Date & Time:** {current_datetime}"
        )
        
        # Basic information
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Account Type:** {info.get('accountType', 'N/A')}")
            st.info(f"**Statement Period:** {info.get('statementPeriod', 'N/A')}")
            st.info(f"**Duration:** {info.get('statementPeriodDuration', 'N/A')}")
        
        with col2:
            # Format bound amount to 2 decimal places
            bound_amount = info.get('boundAmount', 'N/A')
            if bound_amount != 'N/A':
                bound_amount = format_currency(bound_amount)
            st.info(f"**Bound Amount:** {bound_amount}")
            
            if "bankStatementAge" in info:
                st.info(f"**Statement Age:** {info['bankStatementAge']}")
        
        # Explanation
        st.write("**Explanation:**")
        explanation = info.get("explanation", "No explanation provided")
        # Format any currency values in the explanation
        explanation = format_text_with_currency(explanation)
        st.write(explanation)
        
        # Available Documents
        if "availableDocuments" in info:
            st.write("**Available Documents:**")
            for doc in info["availableDocuments"]:
                st.write(f"• {doc}")
        
        # Valid Authentications
        if "validAuthentications" in info and info["validAuthentications"]:
            st.success("**Valid Authentications:**")
            for auth in info["validAuthentications"]:
                st.write(f"✅ {auth.get('element', 'N/A')}: {auth.get('status', 'N/A')}")
        
        # Supported Transactions
        if "supportedTransactions" in info and info["supportedTransactions"]:
            st.write("**Supported Transactions:**")
            for trans in info["supportedTransactions"]:
                st.write(f"• {trans.get('transactionDetail', 'N/A')} - {trans.get('supportType', 'N/A')}")
    
    # Display Issues
    if "Issues" in result and result["Issues"]:
        st.error("**Issues Found:**")
        for issue in result["Issues"]:
            with st.expander(f"❌ {issue.get('type', 'Unknown')} - {issue.get('issue', 'Unknown')}"):
                message = issue.get('message', 'No message')
                # Format currency values in the message
                message = format_text_with_currency(message)
                st.write(message)
                if "details" in issue:
                    st.write("**Details:**")
                    details = issue["details"]
                    for key, value in details.items():
                        if value is not None:
                            # Format currency values in details
                            formatted_value = format_text_with_currency(str(value))
                            st.write(f"• {key}: {formatted_value}")
    
    # Calculation Details (if available)
    if "calculationDetails" in result:
        with st.expander("📊 Calculation Details"):
            details = result["calculationDetails"]
            
            st.markdown("---")
            
            # Check if dependant is True to determine whether to show dependant-related fields (UK only)
            has_dependant = details.get("dependant", False)
            
            # Calculate original exchange rates based on location
            details_with_original = details.copy()
            
            # Fix: Check for both "uk" and "united kingdom"
            location_lower = location.lower()
            is_uk = location_lower in ["uk", "united kingdom"]
            is_australia = location_lower in ["australia", "aus"]
            
            if is_uk and "exchangeRateGBP" in details and exchange_rate_plus > 0:
                exchange_rate_gbp = float(details["exchangeRateGBP"])
                exchange_rate_gbp_original = exchange_rate_gbp / (1 + exchange_rate_plus)
                details_with_original["exchangeRateGBPOriginal"] = exchange_rate_gbp_original
            
            elif is_australia and "exchangeRateAUS" in details and exchange_rate_plus > 0:
                exchange_rate_aus = float(details["exchangeRateAUS"])
                exchange_rate_aus_original = exchange_rate_aus / (1 + exchange_rate_plus)
                details_with_original["exchangeRateAUSOriginal"] = exchange_rate_aus_original
            
            # Define field order based on location
            if is_uk:
                field_order = [
                    "exchangeRateGBPOriginal",
                    "exchangeRateGBP", 
                    "dependant",
                    "boundAmountStudent_PKR",
                    "boundAmountDependant_PKR",
                    "locationStatus",
                    "tuitionFees_PKR",
                    "universityName"
                ]
            else:  # Australia
                field_order = [
                    "exchangeRateAUSOriginal",
                    "exchangeRateAUS",
                    "durationToCheck",
                    "livingExpense_PKR",
                    "oneYearFees_PKR",
                    "travelExpense_PKR"
                ]
            
            # Fields to exclude from display
            excluded_fields = ["totalAmountToCheck", "insideLondon"]
            
            # Display fields in the specified order
            for key in field_order:
                if key in details_with_original and key not in excluded_fields:
                    value = details_with_original[key]
                    
                    # Skip boundAmountDependant_PKR if has_dependant is False (UK only)
                    if is_uk and not has_dependant and key == "boundAmountDependant_PKR":
                        continue
                    
                    # Special handling for dependant field to show Yes/No instead of True/False
                    if key == "dependant":
                        formatted_value = "Yes" if value else "No"
                    else:
                        # Format currency values in calculation details
                        formatted_value = format_text_with_currency(str(value))
                    
                    # Get user-friendly field name
                    friendly_name = get_friendly_field_name(key)
                    
                    st.write(f"**{friendly_name}:** {formatted_value}")
            
            # Display any remaining fields that weren't in the predefined order
            for key, value in details_with_original.items():
                if key not in field_order and key not in excluded_fields:
                    # Skip boundAmountDependant_PKR if has_dependant is False (UK only)
                    if is_uk and not has_dependant and key == "boundAmountDependant_PKR":
                        continue
                    
                    # Special handling for dependant field to show Yes/No instead of True/False
                    if key == "dependant":
                        formatted_value = "Yes" if value else "No"
                    else:
                        # Format currency values in calculation details
                        formatted_value = format_text_with_currency(str(value))
                    
                    # Get user-friendly field name
                    friendly_name = get_friendly_field_name(key)
                    
                    st.write(f"**{friendly_name}:** {formatted_value}")
    
    # All Transactions section continues as before...
    # (Rest of the function remains the same)            
            # Display any remaining fields that weren't in the predefined order
            for key, value in details_with_original.items():
                if key not in field_order and key != "insideLondon":
                    # Skip boundAmountDependant_PKR if has_dependant is False (UK only)
                    if is_uk and not has_dependant and key == "boundAmountDependant_PKR":
                        continue
                    
                    # Special handling for dependant field to show Yes/No instead of True/False
                    if key == "dependant":
                        formatted_value = "Yes" if value else "No"
                    else:
                        # Format currency values in calculation details
                        formatted_value = format_text_with_currency(str(value))
                    
                    # Get user-friendly field name
                    friendly_name = get_friendly_field_name(key)
                    
                    st.write(f"**{friendly_name}:** {formatted_value}")
    
    # All Transactions
    if "allTransactions" in result and result["allTransactions"]:
        with st.expander("📋 All Transactions"):
            transactions = result["allTransactions"]
            st.write(f"Total transactions: {len(transactions)}")
            
            # Create line graph for balance over time
            if transactions:
                # Prepare data for plotting
                dates = []
                balances = []
                transaction_types = []
                amounts = []
                
                for trans in transactions:
                    date_str = trans.get('transactionDate', '')
                    balance_str = trans.get('totalBalanceInAccount', '0')
                    trans_type = trans.get('transactionType', 'Unknown')
                    amount_str = trans.get('transactionAmount', '0')
                    
                    try:
                        # Parse date
                        if date_str:
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                            dates.append(date)
                        else:
                            continue
                            
                        # Parse balance (remove commas and convert to float)
                        balance = float(str(balance_str).replace(',', ''))
                        balances.append(balance)
                        
                        # Store transaction type and amount for hover info
                        transaction_types.append(trans_type)
                        amounts.append(amount_str)
                        
                    except (ValueError, TypeError):
                        continue
                
                if dates and balances:
                    # Create DataFrame for plotting
                    df = pd.DataFrame({
                        'Date': dates,
                        'Balance': balances,
                        'Transaction Type': transaction_types,
                        'Amount': amounts
                    })
                    
                    # Sort by date to ensure proper line connection
                    df = df.sort_values('Date')
                    
                    # Create interactive line chart with Plotly
                    fig = px.line(
                        df, 
                        x='Date', 
                        y='Balance',
                        title='Account Balance Over Time',
                        hover_data={
                            'Transaction Type': True,
                            'Amount': True,
                            'Balance': ':,.2f'
                        }
                    )
                    
                    # Customize the chart
                    fig.update_traces(
                        line=dict(color='#1f77b4', width=2),
                        marker=dict(size=6, color='#1f77b4')
                    )
                    
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Account Balance",
                        height=400,
                        showlegend=False,
                        yaxis=dict(tickformat=',.2f')  # Format y-axis to 2 decimal places
                    )
                    
                    # Display the chart
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add a horizontal line showing the bound amount if available
                    if "Information" in result and "boundAmount" in result["Information"]:
                        bound_amount = result["Information"]["boundAmount"]
                        if isinstance(bound_amount, (int, float)):
                            fig.add_hline(
                                y=bound_amount, 
                                line_dash="dash", 
                                line_color="red",
                                annotation_text=f"Required Amount: {bound_amount:,.2f}",
                                annotation_position="bottom right"
                            )
                            st.plotly_chart(fig, use_container_width=True, key="chart_with_bound")
            
            st.markdown("---")
            st.write("**Transaction Details:**")
            
            # Display all transactions with formatted amounts
            for i, trans in enumerate(transactions):
                transaction_amount = format_currency(trans.get('transactionAmount', 'N/A'))
                balance_amount = format_currency(trans.get('totalBalanceInAccount', 'N/A'))
                
                st.write(f"**{i+1}.** {trans.get('transactionDate', 'N/A')} - "
                        f"{trans.get('transactionType', 'N/A')} - "
                        f"Amount: {transaction_amount} - "
                        f"Balance: {balance_amount}")
                
# Main app
def main():
    st.title("🏦 Bank Statement Analysis Tool")
    st.markdown("Upload and analyze bank statements for tampering, editing, or fabrication detection.")
    
    # Location selection
    location = st.selectbox(
        "Select Location",
        ["Australia", "United Kingdom"],
        help="Choose the country for which you want to analyze the bank statement"
    )
    
    # Common fields
    st.subheader("📄 Document Information")
    
    # Bank Statement input options
    st.write("**Bank Statement** (Required)")
    statement_input_method = st.radio(
        "Choose input method for Bank Statement:",
        ["Upload File", "Provide URL"],
        key="statement_method"
    )
    
    statement_url = None
    statement_file = None
    
    if statement_input_method == "Upload File":
        statement_file = st.file_uploader(
            "Upload Bank Statement PDF",
            type=['pdf'],
            help="Upload the bank statement PDF file",
            key="statement_file"
        )
        if statement_file:
            st.success(f"Bank statement uploaded: {statement_file.name} ({statement_file.size} bytes)")
    else:
        statement_url = st.text_input(
            "Bank Statement URL",
            placeholder="https://example.com/statement.pdf",
            help="URL to the bank statement PDF file",
            key="statement_url"
        )
    
    
    exchange_rate_plus = st.number_input(
        "Exchange Rate Addition (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.1,
        help="Additional percentage to add to the base exchange rate from OANDA. This provides a buffer for exchange rate fluctuations."
    ) / 100  # Convert percentage to decimal
    
    # Location-specific fields
    if location == "Australia":
        st.subheader("🇦🇺 Australia-specific Information")
        
        col1, col2 = st.columns(2)
        with col1:
            one_year_fees = st.number_input(
                "One Year Fees (AUD)*",
                min_value=0.0,
                value=15000.0,
                step=100.0,
                help="Annual tuition fees in Australian Dollars"
            )
        
        with col2:
            duration_to_check = st.number_input(
                "Duration to Check (days)",
                min_value=1,
                max_value=365,
                value=28,
                step=1,
                help="Number of days to check for fund maintenance"
            )
        
        # Supporting Documents input options for Australia
        st.write("**Supporting Documents** (Optional)")
        supporting_input_method = st.radio(
            "Choose input method for Supporting Documents:",
            ["None", "Upload File", "Provide URL"],
            key="supporting_method"
        )
        
        supporting_url = ""
        supporting_file = None
        
        if supporting_input_method == "Upload File":
            supporting_file = st.file_uploader(
                "Upload Supporting Documents PDF",
                type=['pdf'],
                help="Upload supporting documents PDF (salary slips, contracts, etc.)",
                key="supporting_file"
            )
            if supporting_file:
                st.success(f"Supporting documents uploaded: {supporting_file.name} ({supporting_file.size} bytes)")
        elif supporting_input_method == "Provide URL":
            supporting_url = st.text_input(
                "Supporting Documents URL",
                placeholder="https://example.com/supporting_docs.pdf",
                help="URL to supporting documents PDF (salary slips, contracts, etc.)",
                key="supporting_url_input"
            )
        
        # Prepare data for Australia
        analysis_data = {
            "location": "australia",
            "exchangeRatePlus": exchange_rate_plus,
            "OneYearFees": one_year_fees,
            "durationToCheck": duration_to_check,
        }
        
        if statement_url:
            analysis_data["statement_url"] = statement_url
        if supporting_url:
            analysis_data["supporting_url"] = supporting_url
    
    else:  # United Kingdom
        st.subheader("🇬🇧 United Kingdom-specific Information")
        
        university_name = st.text_input(
            "University Name*",
            placeholder="University of Manchester – Manchester, North West",
            help="Full name of the university including location"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            tuition_fees = st.number_input(
                "Tuition Fees (GBP)*",
                min_value=0.0,
                value=21000.0,
                step=100.0,
                help="Annual tuition fees in British Pounds"
            )
        
        with col2:
            dependant = st.checkbox(
                "Has Dependant",
                value=False,
                help="Check if the applicant has dependants"
            )
        
        # Prepare data for UK
        analysis_data = {
            "location": "uk",
            "exchangeRatePlus": exchange_rate_plus,
            "university_name": university_name,
            "tutionFees": tuition_fees,
            "dependant": dependant
        }
        
        if statement_url:
            analysis_data["statement_url"] = statement_url
        
        # UK doesn't have supporting documents, so set to None
        supporting_file = None
    
    # Validation and submission
    st.markdown("---")
    
    # Check required fields
    required_fields_filled = (statement_file is not None or statement_url)
    if location == "Australia":
        required_fields_filled = required_fields_filled and one_year_fees >= 0
    else:
        required_fields_filled = required_fields_filled and university_name and tuition_fees >= 0
    
    if not required_fields_filled:
        st.warning("Please fill in all required fields marked with * and provide a bank statement")
    
    # Submit button
    if st.button("🔍 Analyze Bank Statement", disabled=not required_fields_filled):
        if not statement_file and not statement_url:
            st.error("Please provide a bank statement (either upload a file or provide a URL)")
            return
        
        # Show progress
        with st.spinner("Analyzing bank statement... This may take a few minutes."):
            # Make API request
            if statement_file:
                # Use file upload
                result, status_code = make_api_request_with_files(
                    analysis_data, 
                    statement_file, 
                    supporting_file
                )
            else:
                # Use URL method
                result, status_code = make_api_request_with_urls(analysis_data)
        
        # Display results
        if status_code == 200:
            st.success("Analysis completed successfully!")
            display_analysis_results(result, exchange_rate_plus, location)
        else:
            st.error(f"Analysis failed with status code: {status_code}")
            if "error" in result:
                st.error(f"Error message: {result['error']}")
            else:
                st.json(result)
    
    # Footer
    st.markdown("---")
    st.markdown("**Note:** This tool analyzes bank statements for potential tampering, editing, or fabrication. "
               "The analysis includes authentication checks, fund maintenance verification, and transaction analysis. "
               "Exchange rates are sourced from OANDA with an additional buffer percentage for fluctuations.")

if __name__ == "__main__":
    main()