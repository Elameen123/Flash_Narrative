# bedrock.py
import boto3
import json
import os
import streamlit as st
import time

# --- NEW: Gemini API Client ---
import google.generativeai as genai

# --- NEW: Define Safety Settings ---
# We set to BLOCK_NONE as this is an internal analysis tool
# and we need to analyze all content, even if it's "negative" or "angry".
SAFETY_SETTINGS = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
}

@st.cache_resource
def get_gemini_json_model():
    """
    Initializes and returns the Gemini client configured for JSON output.
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("GOOGLE_API_KEY not found. Please set it in your .env file.")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "response_mime_type": "application/json",
            },
            safety_settings=SAFETY_SETTINGS # <-- ADDED SAFETY SETTINGS
        )
        print("Gemini JSON client initialized successfully.")
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini JSON client: {e}")
        return None

@st.cache_resource
def get_gemini_text_model():
    """
    Initializes and returns the Gemini client configured for text output.
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("GOOGLE_API_KEY not found in .env file.")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            safety_settings=SAFETY_SETTINGS # <-- ADDED SAFETY SETTINGS
        )
        print("Gemini text client initialized successfully.")
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini text client: {e}")
        return None

# --- NEW: Schema for Batch Sentiment Analysis ---
SENTIMENT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": { "type": "INTEGER" },
            "sentiment": {
                "type": "STRING",
                "enum": ["positive", "negative", "neutral", "mixed", "anger", "appreciation"]
            }
        },
        "required": ["id", "sentiment"]
    }
}

# --- NEW: Batch Sentiment Function (replaces get_llm_sentiment) ---
def get_batch_llm_sentiments(text_items: list[dict]):
    """
    Analyzes a batch of texts for sentiment using Gemini with JSON mode.
    text_items should be a list of dicts, e.g., [{"id": i, "text": "..."}]
    Returns a dictionary mapping id -> sentiment.
    """
    model = get_gemini_json_model()
    if not model:
        print("Gemini JSON model not available. Returning empty sentiments.")
        return {}

    # Truncate texts to avoid overly large prompts
    truncated_items = [
        {"id": item["id"], "text": (item.get("text") or "")[:500]}
        for item in text_items
    ]

    prompt = f"""
    Analyze the sentiment for each text item in the following JSON list.
    Respond with only a JSON array matching the provided schema.
    Classify sentiment as one of: positive, negative, neutral, mixed, anger, appreciation.
    If a text is purely informational, classify it as neutral.

    TEXT ITEMS:
    {json.dumps(truncated_items)}
    """

    generation_config = {
        "response_mime_type": "application/json",
        "response_schema": SENTIMENT_SCHEMA
    }

    max_retries = 5
    delay = 1
    for attempt in range(max_retries):
        try:
            print(f"Attempting batch sentiment analysis (Attempt {attempt + 1})...")
            response = model.generate_content(
                contents=prompt,
                generation_config=generation_config
            )

            # --- UPDATED: Robust response checking ---
            if not response.candidates or response.candidates[0].finish_reason.name != "STOP":
                reason = "UNKNOWN"
                if response.candidates:
                    reason = response.candidates[0].finish_reason.name
                elif response.prompt_feedback:
                    reason = response.prompt_feedback.block_reason.name
                
                print(f"Batch sentiment generation stopped. Finish Reason: {reason}")
                # Don't retry if blocked, just fail
                break

            # This part is now safe to run
            response_json = json.loads(response.text)

            # Convert list of objects to a lookup dictionary
            sentiment_map = {item['id']: item['sentiment'] for item in response_json}
            print(f"Successfully processed {len(sentiment_map)} sentiments.")
            return sentiment_map

        except Exception as e:
            print(f"Error generating batch sentiment (Attempt {attempt + 1}/{max_retries}): {e}")
            if "json" in str(e).lower():
                print(f"Invalid JSON response from model.")
                # Don't retry on bad JSON, it's a prompt/model issue
                break
            # Implement exponential backoff
            time.sleep(delay)
            delay *= 2

    print("Failed to get batch sentiments after retries.")
    return {} # Return empty map on failure


# --- UPDATED Report Summary Function (using Gemini) ---
def generate_llm_report_summary(kpis, top_keywords, articles, brand, competitors): # Added competitors
    """
    Generates a more comprehensive, professional report summary and recommendations
    using Gemini. Includes competitive context.
    Returns report text (Markdown formatted) or error message.
    """
    model = get_gemini_text_model()
    if not model:
        print("Gemini text model not available. Cannot generate LLM report summary.")
        return ("**Error:** Could not connect to Gemini client.\n"
                "**Recommendations:** Review data manually.")

    # --- Prepare Data Summary for Prompt (No changes here) ---
    sentiment_summary = ", ".join([f"{k.capitalize()}: {v:.1f}%" for k,v in kpis.get('sentiment_ratio', {}).items()])
    sov_summary = ""
    all_brands_list = kpis.get('all_brands', [brand] + (competitors or []))
    sov_values = kpis.get('sov', [])
    if len(sov_values) != len(all_brands_list):
         from collections import Counter # Quick import
         brand_counts = Counter()
         for item in articles:
              mentioned = item.get('mentioned_brands', [])
              present_brands = set()
              if isinstance(mentioned, list): present_brands.update(b for b in mentioned if b in all_brands_list)
              elif isinstance(mentioned, str) and mentioned in all_brands_list: present_brands.add(mentioned)
              for b in present_brands: brand_counts[b] += 1
         total_sov_mentions = sum(brand_counts.values())
         sov_values = [(brand_counts[b] / total_sov_mentions * 100) if total_sov_mentions > 0 else 0 for b in all_brands_list]

    if len(sov_values) == len(all_brands_list):
        sov_items = [f"{b}: {s:.1f}%" for b, s in zip(all_brands_list, sov_values)]
        sov_summary = ", ".join(sov_items)

    data_summary = f"""
    **Brand:** {brand}
    **Competitors Tracked:** {', '.join(competitors) if competitors else 'None'}
    **Key Performance Indicators (KPIs):**
    * Sentiment Ratio: {sentiment_summary if sentiment_summary else 'N/A'}
    * Share of Voice (SOV): {sov_summary if sov_summary else 'N/A'}
    * Media Impact Score (MIS): {kpis.get('mis', 0):.0f}
    * Message Penetration Index (MPI): {kpis.get('mpi', 0):.1f}%
    * Avg. Social Engagement: {kpis.get('engagement_rate', 0):.1f}
    * Total Reach: {kpis.get('reach', 0):,}
    **Top Keywords/Phrases Mentioned:** {', '.join([k[0] for k in top_keywords]) if top_keywords else 'None identified'}
    **Recent Positive/Appreciative Headlines for {brand}:**
    {[a['text'][:150] for a in articles if brand.lower() in (mb.lower() for mb in a.get('mentioned_brands',[])) and a.get('sentiment') in ['positive', 'appreciation']][:3]}
    **Recent Negative/Angry Headlines for {brand}:**
    {[a['text'][:150] for a in articles if brand.lower() in (mb.lower() for mb in a.get('mentioned_brands',[])) and a.get('sentiment') in ['negative', 'anger']][:3]}
    **Notable Competitor Headlines:**
    {[a['text'][:150] for a in articles if any(c.lower() in (mb.lower() for mb in a.get('mentioned_brands',[])) for c in competitors)][:3]}
    """

    # --- Define the Enhanced Prompt (No changes here) ---
    prompt = f"""
Human: You are a senior Public Relations analyst creating a concise report for the client, '{brand}'.
Analyze the provided data summary, focusing on brand sentiment, market visibility (SOV compared to competitors: {', '.join(competitors)}), key discussion themes, and overall media impact.

Based *only* on the data below, generate a report with these Markdown sections:

**1. Executive Summary:** (2-3 bullet points)
    * Overview of '{brand}'s online reputation (sentiment ratio, MIS).
    * '{brand}'s visibility vs. competitors (SOV).
    * Critical emerging themes (positive/negative keywords or headlines).

**2. Key Findings:** (3-4 bullet points)
    * Dominant sentiment drivers (positive/negative percentages if significant).
    * Share of Voice analysis: Is '{brand}' leading/lagging?
    * Message Penetration (MPI): Are campaign messages resonating? ({kpis.get('mpi', 0):.1f}% detected).
    * Significant positive/negative headlines for '{brand}'.
    * Brief note on any major competitor activity observed in headlines.

**3. PR Recommendations:** (3-4 actionable bullet points)
    * Concrete actions based on findings.
    * Examples: Amplify positive themes (keywords/headlines), address negative feedback, adjust messaging based on MPI, counter competitor narratives (SOV/headlines), leverage high-impact (MIS) coverage.
    * Link recommendations directly to data (sentiment, SOV, MPI, keywords, headlines).

**Do NOT add greetings or sentences outside these sections.** Use professional language.

<data_summary>
{data_summary}
</data_summary>

Assistant:
"""

    # --- Call Gemini with Retry Logic ---
    text_generation_config = {
        "temperature": 0.6,
        "max_output_tokens": 1000
    }

    max_retries = 5
    delay = 1
    for attempt in range(max_retries):
        try:
            print(f"Attempting report generation (Attempt {attempt + 1})...")
            response = model.generate_content(
                contents=prompt,
                generation_config=text_generation_config
            )

            # --- UPDATED: Robust response checking ---
            if not response.candidates or response.candidates[0].finish_reason.name != "STOP":
                reason = "UNKNOWN"
                if response.candidates:
                    reason = response.candidates[0].finish_reason.name
                elif response.prompt_feedback:
                    reason = response.prompt_feedback.block_reason.name
                
                print(f"Report generation stopped. Finish Reason: {reason}")
                # Raise an exception to trigger retry or failure
                raise Exception(f"Gemini API block. Finish Reason: {reason}")

            result_text = response.text
            if result_text:
                if "**Executive Summary:**" not in result_text or "**Key Findings:**" not in result_text or "**PR Recommendations:**" not in result_text:
                    print(f"Model report format unexpected (missing sections): {result_text[:150]}...")
                return result_text
            else:
                raise Exception("Empty response from model")

        except Exception as e:
            print(f"Error generating report summary (Attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(delay)
            delay *= 2

    # Fallback error message if all retries fail
    return ("**Error:** Could not generate AI Report Summary using Gemini after retries.\n"
            "This was likely due to a persistent safety block on the input data.\n"
            "Please check your GOOGLE_API_KEY and network connection.\n\n"
            "**Recommendations:** Review raw data and KPIs manually.")



# # --- Bedrock Client Setup (COMMENTED OUT) ---
# @st.cache_resource
# def get_bedrock_client():
#     """Initializes and returns the Bedrock runtime client, caching the resource."""
#     try:
#         aws_region = os.getenv("AWS_REGION", "us-east-1") # Default region
#         if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_KEY"):
#             st.error("AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_KEY) not found. Please set them in your .env file.")
#             return None
#
#         bedrock_client = boto3.client(
#             service_name="bedrock-runtime",
#             region_name=aws_region,
#             aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#             aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
#         )
#         print(f"Bedrock client initialized successfully for region {aws_region}.")
#         return bedrock_client
#     except Exception as e:
#         st.error(f"Error initializing Bedrock client: {e}")
#         return None
#
# # --- Model Configuration (COMMENTED OUT) ---
# PREFERRED_TEXT_MODELS = [
#     "anthropic.claude-3-opus-20240229-v1:0",
#     "global.anthropic.claude-sonnet-4-20250514-v1:0",
#     "anthropic.claude-3-sonnet-20240229-v1:0",
#     "meta.llama3-70b-instruct-v1:0",
#     "cohere.command-r-plus-v1:0",
#     "mistral.mistral-large-2402-v1:0",
#     "amazon.titan-text-express-v1",
#     "anthropic.claude-3-haiku-20240307-v1:0",
#     "amazon.titan-text-lite-v1",
# ]
#
# # --- Helper Functions for Different Model Payloads (COMMENTED OUT) ---
#
# def _build_anthropic_body(prompt, max_tokens=10, temperature=0.1):
#     """Builds the JSON body for Anthropic Claude models."""
#     return json.dumps({
#         "anthropic_version": "bedrock-2023-05-31",
#         "max_tokens": max_tokens,
#         "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
#         "temperature": temperature,
#     })
#
# def _parse_anthropic_response(response_body_json):
#     """Parses the response from Anthropic Claude models."""
#     content = response_body_json.get('content', [])
#     if content and isinstance(content, list) and len(content) > 0:
#         return content[0].get('text', '').strip()
#     return None
#
# (All other _build_... and _parse_... functions are also commented out)
# ...
#
# # --- Main API Call Function with Fallback (COMMENTED OUT) ---
#
# def invoke_model_sequentially(prompt, model_list, max_tokens, temperature):
#     """
#     Tries to invoke models from the list sequentially until one succeeds.
#     Returns the successful model's output or None if all fail.
#     """
#     bedrock_client = get_bedrock_client()
#     if not bedrock_client:
#         print("Bedrock client not available.")
#         return None
#
#     last_error = "No models attempted or all skipped."
#
#     for model_id in model_list:
#         (All logic inside the loop is commented out)
#         ...
#
#     print(f"All models failed. Last error: {last_error}")
#     st.error(f"AI models failed. Last error: {last_error}. Using keyword fallback.")
#     return None
#
#
# # --- Updated Sentiment Function (COMMENTED OUT - REPLACED BY BATCH) ---
# def get_llm_sentiment(text_chunk):
#     """
#     Analyzes sentiment using Bedrock with model fallback.
#     Returns sentiment string or None if all models fail.
#     """
#     text_chunk = (text_chunk or "")[:500]
#     prompt = f"""
# Human: Carefully analyze the sentiment expressed in the following text. ...
# <text>
# {text_chunk}
# </text>
# Assistant:
# """
#     result_text = invoke_model_sequentially(
#         prompt=prompt, model_list=PREFERRED_TEXT_MODELS, max_tokens=10, temperature=0.1
#     )
#
#     if result_text:
#         sentiment = result_text.lower().strip().replace(".", "")
#         valid_sentiments = ['positive', 'negative', 'neutral', 'mixed', 'anger', 'appreciation']
#         if sentiment in valid_sentiments:
#             return sentiment
#         else:
#             if "positive" in sentiment: return "positive"
#             if "negative" in sentiment: return "negative"
#             if "neutral" in sentiment: return "neutral"
#             print(f"Model returned unexpected sentiment text: '{sentiment}'. Treating as failure.")
#             return None
#     else:
#         return None

