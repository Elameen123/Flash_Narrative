import os
import google.generativeai as genai
import json
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("⚠️ GEMINI_API_KEY not found in .env file.")

genai.configure(api_key=api_key)

def get_gemini_model():
    """Returns the configured Gemini model instance."""
    # Using gemini-1.5-flash for speed and cost-efficiency (perfect for dashboards)
    # Use gemini-1.5-pro if you need deeper reasoning
    return genai.GenerativeModel('gemini-2.5-flash')

def get_batch_llm_sentiments(items):
    """
    Analyzes a list of text items for sentiment using Gemini.
    Input: [{'id': 0, 'text': '...'}, ...]
    Output: {0: 'positive', 1: 'negative', ...}
    """
    if not items:
        return {}

    try:
        model = get_gemini_model()
        
        # Prepare the prompt for batch processing
        prompt_text = "Analyze the sentiment of the following texts. Return ONLY a raw JSON object where keys are the IDs and values are one of: 'positive', 'negative', 'neutral', 'anger', 'appreciation', 'mixed'.\n\nTexts:\n"
        
        # Limit batch size to prevent token overflow (chunking logic can be added for massive lists)
        for item in items[:30]: # Limit to 30 for speed in this demo
            prompt_text += f"ID {item['id']}: {item['text'][:300]}\n"

        # Generate content with JSON instruction
        response = model.generate_content(
            prompt_text,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Parse JSON
        sentiment_map = json.loads(response.text)
        
        # Ensure keys are integers (JSON keys are strings by default)
        return {int(k): v for k, v in sentiment_map.items()}

    except Exception as e:
        print(f"Gemini Batch Error: {e}")
        # traceback.print_exc()
        return {}

def generate_llm_report_summary(kpis, top_keywords, full_data, brand, competitors):
    """
    Generates a professional executive summary using Gemini.
    """
    try:
        model = get_gemini_model()
        
        # Construct a context summary for the LLM
        context = f"""
        Brand: {brand}
        Competitors: {', '.join(competitors)}
        KPIs:
        - Media Impact Score (MIS): {kpis.get('mis', 0)}
        - Message Penetration (MPI): {kpis.get('mpi', 0)}%
        - Engagement Rate: {kpis.get('engagement_rate', 0)}
        - Total Reach: {kpis.get('reach', 0)}
        
        Top Keywords: {', '.join([w[0] for w in top_keywords[:10]])}
        
        Recent Headlines:
        {chr(10).join([f"- {i.get('text', '')[:100]} ({i.get('sentiment')})" for i in full_data[:5]])}
        """
        
        prompt = f"""
        You are a Senior PR Crisis Manager. Based on the data below, write a concise Executive Summary (max 300 words).
        
        Structure:
        1. **Overview**: High-level sentiment summary.
        2. **Key Drivers**: What is driving the positive/negative sentiment?
        3. **Strategic Recommendation**: One actionable step the brand should take immediately.
        
        Data:
        {context}
        
        Output Format: Standard Markdown.
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Gemini Summary Error: {e}")
        return "⚠️ AI Summary could not be generated due to a connection error."