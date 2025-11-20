import pandas as pd
import streamlit as st
import os

# --- Constants ---
DATA_FILE = "demo_data.csv"
SUMMARY_FILE = "demo_ai_summary.txt"

# --- Main Functions ---

@st.cache_data(ttl=600) # Cache the data for 10 minutes
def load_data_from_csv():
    """
    Loads the demo data from the CSV file.
    - Case-insensitive headers.
    - Renames "Mention Text" to "text".
    - Safely cleans and converts Likes, Comments, and Reach to numbers.
    - Adds default 'authority' and 'theme' if missing.
    """
    try:
        df = pd.read_csv(DATA_FILE)
        
        # --- NEW ROBUST LOADER ---
        # 1. Standardize all column headers: lowercase and stripped of spaces
        df.columns = [str(col).lower().strip() for col in df.columns]

        # 2. Define the mapping from YOUR CSV to what the APP EXPECTS
        column_map = {
            "date": "date",
            "source": "source",
            "mention text": "text", # <-- This is the key rename
            "link": "link",
            "likes": "likes",
            "comments": "comments",
            "reach": "reach",
            "headline": "headline"
            # We will IGNORE 'headline' and 'mentioned_brand'
        }
        
        # 3. Rename the columns we care about
        df = df.rename(columns=column_map)

        # 4. Check for essential columns (text, date, source)
        required_cols = ['text', 'date', 'source']
        missing_essentials = set(required_cols) - set(df.columns)
        if missing_essentials:
            st.error(f"Demo data CSV is invalid! It MUST contain: {', '.join(required_cols)}")
            return []

        # 5. Add default values for optional KPI columns if they weren't found
        if 'likes' not in df.columns: df['likes'] = 0
        if 'comments' not in df.columns: df['comments'] = 0
        if 'reach' not in df.columns: df['reach'] = 1000
        if 'authority' not in df.columns: df['authority'] = 5
        if 'theme' not in df.columns: df['theme'] = 'General News' # Will be overwritten

        # 6. --- CRITICAL: Clean the numeric columns ---
        # This fixes the "50,000" and empty (,,) problems
        for col in ['likes', 'comments', 'reach']:
            if col in df.columns:
                # Convert to string, remove quotes, remove commas
                df[col] = df[col].astype(str).str.replace('"', '').str.replace(',', '')
                # Fill empty/NaN values with '0'
                df[col] = df[col].fillna('0')
                # Convert to numeric, forcing errors to 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        # --- END OF CLEANING ---
            
        print("Demo data loaded, cleaned, and columns mapped successfully.")
        return df.to_dict('records')
        
    except FileNotFoundError:
        st.error(f"FATAL: '{DATA_FILE}' not found! Please add it to the root folder.")
        return []
    except Exception as e:
        st.error(f"An error occurred while loading {DATA_FILE}: {e}")
        return []

@st.cache_data(ttl=3600) # Cache the summary for 1 hour
def load_ai_summary():
    """Load the pre-written AI summary from file"""
    file_path = 'demo_ai_summary.txt'
    
    if not os.path.exists(file_path):
        return "**AI Summary:** File not found. Please ensure demo_ai_summary.txt exists in the project root."
    
    try:
        # Try UTF-8 first (most common for text files with special characters)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 which can read any byte sequence
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"**Error:** Could not read AI summary: {str(e)}"
    except Exception as e:
        return f"**Error:** {str(e)}"


# --- Self-Test (for debugging) ---
if __name__ == "__main__":
    print("Running demo_loader.py self-test...")
    data = load_data_from_csv()
    if data:
        print(f"Successfully loaded {len(data)} mentions.")
        print("First mention sample (after cleaning):")
        if data[0]:
            print({
                'text': data[0].get('text', 'N/A')[:50] + "...",
                'reach': data[0].get('reach', 'N/A'),
                'likes': data[0].get('likes', 'N/A'),
                'comments': data[0].get('comments', 'N/A')
            })
    else:
        print("Data loading FAILED.")