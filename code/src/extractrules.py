import streamlit as st
import pandas as pd
import spacy
import pdfplumber
from transformers import pipeline

# Load NLP models
nlp = spacy.load("en_core_web_sm")
ner_pipeline = pipeline("ner", model="dslim/bert-base-NER")



# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# Function to extract rules from the PDF text
def extract_rules(text):
    doc = nlp(text)
    extracted_rules = []

    for sent in doc.sents:
        entities = ner_pipeline(sent.text)
        conditions = [ent['word'] for ent in entities if ent['entity'].startswith("B-")]

        # Identify rule-related keywords
        keywords = ["must", "should", "shall", "not allowed", "cannot", "only if", "required"]
        if any(word in sent.text.lower() for word in keywords):
            structured_rule = {
                "rule": sent.text,
                "conditions": conditions,
                "field": "Account_Balance" if "account balance" in sent.text.lower() else 
                         "RiskScore" if "risk score" in sent.text.lower() else
                         "Transaction_Amount" if "transaction amount" in sent.text.lower() else None,
                "operator": "< 0" if "not be negative" in sent.text.lower() else 
                            "> 5" if "greater than 5" in sent.text.lower() else
                            "==" if "must match" in sent.text.lower() else None
            }
            extracted_rules.append(structured_rule)

    return extracted_rules

# Function to validate rules against CSV data
def validate_rules(rules, df):
   # validation_results = []
    violations = []

    for rule in rules:
        st.write("hello")
        #rule_text = rule["rule"].lower()
        field = rule["field"]
        operator = rule["operator"]
        condition = rule.get('condition')
        validation_type = rule.get('validation_type')

        
        
         # Check if field exists
        if field not in df.columns:
            violations.append({
                'rule_id': rule_id,
                'field': field,
                'issue': 'Field does not exist in the dataset',
                'sample_data': None
            })
            continue
        
        # Apply different checks based on validation type
        if validation_type == 'value_range':
            # Extract min and max values from condition
            import re
            range_match = re.search(r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)', condition, re.IGNORECASE)
            if range_match:
                min_val = float(range_match.group(1))
                max_val = float(range_match.group(2))
                
                # Check for violations
                mask = (df[field] < min_val) | (df[field] > max_val)
                if mask.any():
                    sample_violations = df.loc[mask].head(5)
                    violations.append({
                        'rule_id': rule_id,
                        'field': field,
                        'issue': f'Values outside range {min_val} to {max_val}',
                        'sample_data': sample_violations[field].tolist()
                    })
        
        elif validation_type == 'format_check':
            # Use regex pattern in condition
            pattern_match = re.search(r'pattern\s+(.*)', condition, re.IGNORECASE)
            if pattern_match:
                pattern = pattern_match.group(1).strip('"\'')
                
                # Check for violations using regex
                mask = ~df[field].astype(str).str.match(pattern)
                if mask.any():
                    sample_violations = df.loc[mask].head(5)
                    violations.append({
                        'rule_id': rule_id,
                        'field': field,
                        'issue': f'Values do not match pattern {pattern}',
                        'sample_data': sample_violations[field].tolist()
                    })
        
        # Add more validation types as needed
        
    return violations if violations else ["✅ No violations found!"]

       
    #return validation_results if validation_results else ["✅ No violations found!"]

# Streamlit UI
st.title("📜 Rule Extraction & Validation from PDF")
st.sidebar.header("Upload Files")

# Upload PDF
uploaded_pdf = st.sidebar.file_uploader("Upload a PDF file", type=["pdf"])

# Upload CSV
uploaded_csv = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_pdf and uploaded_csv:
    st.success("✅ Files uploaded successfully!")

    # Extract text from PDF
    pdf_text = extract_text_from_pdf(uploaded_pdf)
    st.subheader("📄 Extracted Text from PDF")
    st.text_area("Extracted Text", pdf_text[:1000], height=200)

    # Extract rules
    rules = extract_rules(pdf_text)
    st.subheader("📜 Extracted Rules")
    for idx, rule in enumerate(rules, 1):
        st.write(f"**{idx}.** {rule['rule']} (Conditions: {rule['conditions']})")

    # Load CSV
    df = pd.read_csv(uploaded_csv)

    # Validate rules against CSV
    validation_results = validate_rules(rules, df)
    st.subheader("✅ Validation Results")
    for result in validation_results:
        st.write(result)

else:
    st.warning("⚠️ Please upload both a PDF and a CSV file.")
