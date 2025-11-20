import streamlit as st
import pandas as pd
import plotly.express as px
import traceback
import io
from collections import Counter
import os
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Helper function to load images for CSS ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    """ Reads a binary file and returns its Base64 encoded string. """
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading image {bin_file}: {e}")
        return None

# --- Page Config ---
st.set_page_config(
    page_title="Dashboard | Flash Narrative",
    page_icon="fn logo.jpeg",
    layout="wide"
)

# --- Imports (Gemini Switched) ---
try:
    from .. import analysis
    from .. import report_gen
    from .. import demo_loader 
    from .. import scraper      
    from .. import gemini_integration as gemini_llm  # <--- CHANGED: Use Gemini
    from .. import gmail_api_integration as servicenow_integration
except ImportError:
    # Fallback for local testing
    import analysis, report_gen, demo_loader, scraper, gemini_integration as gemini_llm, gmail_api_integration as servicenow_integration
except Exception as e:
    st.error(f"Failed to import modules: {e}")
    st.stop()


# --- Brand Colors & Custom CSS ---
GOLD = "#FFD700"; BLACK = "#000000"; BEIGE = "#F5F5DC"
DARK_BG = "#1E1E1E"; LIGHT_TEXT = "#EAEAEA"
GREEN_BG = "#28a745"; RED_BG = "#dc3545"

bg_image_base64 = get_base64_of_bin_file("fn text.jpeg") 
bg_image_css = f"""
    .stApp::before {{
        content: "";
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-image: url("data:image/jpeg;base64,{bg_image_base64}");
        background-position: center; background-repeat: no-repeat; background-size: cover; 
        opacity: 0.05; z-index: -1; 
    }}
""" if bg_image_base64 else ""

custom_css = f"""
<style>
    {bg_image_css}
    .stApp {{ background-color: transparent; color: {LIGHT_TEXT}; }}
    [data-testid="stAppViewContainer"] > .main {{ background-color: {DARK_BG}; }}
    
    /* Sidebar & Headers */
    [data-testid="stSidebar"] > div:first-child {{ background-color: {BLACK}; border-right: 1px solid {GOLD}; }}
    .stApp h1, .stApp h2, .stApp h3 {{ color: {GOLD}; }}
    
    /* Buttons */
    .stButton>button {{ background-color: {GOLD}; color: {BLACK}; border: 1px solid {GOLD}; border-radius: 5px; }}
    .stButton>button:hover {{ background-color: {BLACK}; color: {GOLD}; border: 1px solid {GOLD}; }}
    
    /* Tables */
    .stDataFrame {{ border: 1px solid {BEIGE}; border-radius: 5px; }}
    .stDataFrame thead th {{ background-color: {BLACK}; color: {GOLD}; }}
    
    /* KPI Boxes */
    .kpi-box {{ border: 1px solid {BEIGE}; border-radius: 5px; padding: 15px; text-align: center; margin-bottom: 10px; background-color: {DARK_BG}; }}
    .kpi-box .label {{ font-size: 0.9em; color: {BEIGE}; margin-bottom: 5px; text-transform: uppercase; height: 2.4em; display: flex; align-items: center; justify-content: center; }}
    .kpi-box .value {{ font-size: 1.5em; font-weight: bold; color: {LIGHT_TEXT}; }}
    .kpi-box.good {{ background-color: {GREEN_BG}; border-color: {GREEN_BG}; }}
    .kpi-box.good .label, .kpi-box.good .value {{ color: {BLACK}; }}
    .kpi-box.bad {{ background-color: {RED_BG}; border-color: {RED_BG}; }}
    .kpi-box.bad .label, .kpi-box.bad .value {{ color: {LIGHT_TEXT}; }}
    
    /* Logo Styling */
    div[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stImage"] img {{
        border-radius: 50%; border: 2px solid {GOLD}; box-shadow: 0 0 10px {GOLD};
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


def run_smart_analysis(brand, competitors, industry, campaign_messages, hours, time_range_text):
    """
    Hybrid Logic: Scrape + Gemini (Live) -> Fallback to Demo CSV.
    """
    st.session_state.analysis_mode = "Initializing..."
    
    # --- ATTEMPT 1: LIVE MODE ---
    try:
        st.divider()
        st.caption("🚀 Attempting Live Connection...")
        
        # 1. Scrape Data
        with st.spinner(f"Searching live web data for '{brand}'..."):
            # Passing competitors allows scraper to be smarter about context
            scraped_result = scraper.fetch_all(brand=brand, time_frame=hours, competitors=competitors, industry=industry)
        
        if not scraped_result or not scraped_result.get('full_data'):
            raise ValueError("Scraper returned no data (check internet or search terms).")

        temp_data = scraped_result['full_data']
        
        # 2. Gemini AI Analysis
        st.write("🧠 Connecting to Gemini AI for analysis...")
        progress_bar = st.progress(0, text="Preparing AI batch...")
        
        items_to_analyze = [{"id": i, "text": item.get("text", "")} for i, item in enumerate(temp_data)]
        
        # Call Gemini Wrapper (Updated from Bedrock)
        sentiment_map = gemini_llm.get_batch_llm_sentiments(items_to_analyze)
        
        # Apply Sentiments
        for i, item in enumerate(temp_data):
            llm_sentiment = sentiment_map.get(i)
            # Fallback to keyword if AI fails for specific item
            item['sentiment'] = llm_sentiment if llm_sentiment else analysis.analyze_sentiment_keywords(item.get('text', ''))
            
            progress_percent = (i + 1) / len(temp_data)
            progress_bar.progress(progress_percent, text=f"AI Analysis: {int(progress_percent*100)}%")
            
        progress_bar.empty()
        
        # 3. Store Live Data
        st.session_state.full_data = temp_data
        st.session_state.analysis_mode = "LIVE"
        st.toast("✅ Live Analysis Complete!", icon="🌐")

    # --- ATTEMPT 2: FALLBACK DEMO MODE ---
    except Exception as e:
        st.warning(f"⚠️ Live connection failed. Switching to Offline/Demo Mode.\n(Error: {str(e)})")
        try:
            with st.spinner("Loading offline demo data..."):
                full_data = demo_loader.load_data_from_csv()
            if not full_data: st.error("Critical: Demo data missing!"); st.stop()
            
            st.session_state.full_data = full_data
            st.session_state.analysis_mode = "DEMO"
            st.toast("⚠️ Using Demo Data", icon="📂")
        except Exception as demo_e:
            st.error(f"Fatal Error: {demo_e}"); st.stop()

    # --- COMMON STEPS (KPIs) ---
    try:
        with st.spinner("Calculating KPIs..."):
            # New Analysis function now accepts 'competitors' and 'hours'
            kpi_results = analysis.compute_kpis(
                full_data=st.session_state.full_data,
                campaign_messages=campaign_messages,
                brand=brand,
                competitors=competitors, 
                industry=industry,
                hours=hours
            )
            st.session_state.kpis = kpi_results
            
            all_text = " ".join([item.get("text", "") for item in st.session_state.full_data])
            st.session_state.top_keywords = analysis.extract_keywords(all_text, brand, competitors)
            
        st.success(f"Dashboard Updated ({st.session_state.analysis_mode} Mode)")

        # Check Alerts
        sentiment_ratio = st.session_state.kpis.get('sentiment_ratio', {})
        neg_pct = sentiment_ratio.get('negative', 0) + sentiment_ratio.get('anger', 0)
        if neg_pct > 30:
            alert_msg = f"ALERT: High negative sentiment ({neg_pct:.1f}%) detected for {brand}."
            st.error(alert_msg)
            if st.session_state.analysis_mode == "LIVE":
                alert_email = os.getenv("ALERT_EMAIL")
                servicenow_integration.send_alert(alert_msg, channel='#alerts', to_email=alert_email)
    
    except Exception:
        st.error(f"Calculation Error:\n{traceback.format_exc()}")


def display_dashboard(brand, competitors, time_range_text, thresholds):
    """ Visualizes the data stored in Session State. """
    if not st.session_state.kpis:
        st.info("Click 'Run Analysis' to start."); return

    mode = st.session_state.get("analysis_mode", "UNKNOWN")
    st.markdown(f"**Status: {'🟢 Online (Live Data)' if mode == 'LIVE' else '🟠 Offline (Demo Data)'}**")

    st.subheader("Key Performance Indicators")
    kpis = st.session_state.kpis
    mis_val = kpis.get('mis', 0); mpi_val = kpis.get('mpi', 0)
    eng_val = kpis.get('engagement_rate', 0); reach_val = kpis.get('reach', 0)
    
    # KPI Boxes
    c1, c2, c3, c4 = st.columns(4)
    def get_class(val, thresh): return "good" if val >= thresh else "bad"
    
    with c1: st.markdown(f'<div class="kpi-box {get_class(mis_val, thresholds["mis_good"])}"><div class="label">Media Impact (MIS)</div><div class="value">{mis_val:.0f}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-box {get_class(mpi_val, thresholds["mpi_good"])}"><div class="label">Msg Penetration (MPI)</div><div class="value">{mpi_val:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-box {get_class(eng_val, thresholds["eng_good"])}"><div class="label">Avg Social Engagement</div><div class="value">{eng_val:.1f}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kpi-box {get_class(reach_val, thresholds["reach_good"])}"><div class="label">Total Reach</div><div class="value">{reach_val:,}</div></div>', unsafe_allow_html=True)

    # --- NEW: CAMPAIGN DEEP DIVE ---
    st.markdown("---")
    st.subheader("🎯 Campaign Intelligence")
    camp_data = kpis.get('campaign_data', {})
    
    if not camp_data:
        st.info(f"No mentions matching campaign messages for '{brand}' were found in this timeframe.")
    else:
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Campaign Sentiment**")
            st.caption("How people feel specifically about your campaign messages.")
            cs_ratio = camp_data.get('sentiment', {})
            if cs_ratio:
                df_cs = pd.DataFrame({'Sentiment': list(cs_ratio.keys()), 'Percent': list(cs_ratio.values())})
                fig_cs = px.pie(df_cs, names='Sentiment', values='Percent', color='Sentiment', 
                                color_discrete_map={'positive':'green','negative':'red','neutral':'grey'})
                st.plotly_chart(fig_cs, use_container_width=True)
        with cc2:
            st.markdown("**Context Keywords**")
            st.caption("Words most frequently used alongside your campaign.")
            ck_words = camp_data.get('keywords', [])
            if ck_words:
                df_ck = pd.DataFrame(ck_words, columns=['Keyword', 'Frequency'])
                fig_ck = px.bar(df_ck, x='Frequency', y='Keyword', orientation='h')
                fig_ck.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_ck, use_container_width=True)
        
        with st.expander(f"View {camp_data.get('mentions_count', 0)} Campaign Mentions"):
            for item in camp_data.get('mentions', []):
                st.markdown(f"**{item.get('source')}** ({item.get('sentiment')}): {item.get('text')}")
                st.markdown("---")

    # --- General Charts ---
    st.markdown("---")
    st.subheader("Visual Analysis")
    
    # Sentiment Pie
    sentiment_ratio = kpis.get("sentiment_ratio", {})
    if sentiment_ratio:
        pie_data = pd.DataFrame({'Sentiment': list(sentiment_ratio.keys()), 'Percent': list(sentiment_ratio.values())})
        fig_pie = px.pie(pie_data, names='Sentiment', values='Percent', title=f"Overall Sentiment ({mode})", color='Sentiment', color_discrete_map={'positive':'green','negative':'red','neutral':'grey'})
        st.plotly_chart(fig_pie, use_container_width=True)

    # Share of Voice
    all_brands = kpis.get("all_brands", [brand] + competitors)
    sov_values = kpis.get("sov", [])
    # Safety check for SOV length mismatch
    if len(sov_values) == len(all_brands):
        sov_df = pd.DataFrame({'Brand': all_brands, 'Share of Voice (%)': sov_values})
        fig_sov = px.bar(sov_df, x='Brand', y='Share of Voice (%)', title="Share of Voice", color='Brand')
        st.plotly_chart(fig_sov, use_container_width=True)

    # --- Mentions Table ---
    st.subheader("Recent Mentions")
    if st.session_state.full_data:
        display_data = [{'Sentiment': i.get('sentiment'), 'Source': i.get('source'), 'Mention': i.get('text', '')[:150]+"...", 'Link': i.get('link')} for i in st.session_state.full_data[:30]]
        st.dataframe(pd.DataFrame(display_data), column_config={"Link": st.column_config.LinkColumn("Link")}, use_container_width=True, hide_index=True)

    # --- Reporting Section ---
    st.subheader("Generate & Send Report")
    recipient_email = st.text_input("Enter Email to Send Reports To:", placeholder="your.email@example.com")

    if st.button("Generate Reports", use_container_width=True):
        st.session_state.report_generated = False
        pdf_generated = False; excel_generated = False
        
        # 1. AI Summary
        with st.spinner("Drafting Executive Summary (Gemini)..."):
            if st.session_state.analysis_mode == "LIVE":
                try:
                    # Use Gemini Integration
                    ai_summary = gemini_llm.generate_llm_report_summary(
                        st.session_state.kpis, st.session_state.top_keywords, 
                        st.session_state.full_data, brand, competitors
                    )
                    st.session_state.ai_summary_text = ai_summary
                except Exception as e:
                    st.error(f"Gemini Error: {e}. Using fallback."); st.session_state.ai_summary_text = demo_loader.load_ai_summary()
            else:
                st.session_state.ai_summary_text = demo_loader.load_ai_summary()

        # 2. PDF
        with st.spinner("Building PDF..."):
            try:
                md, pdf_bytes = report_gen.generate_report(
                    kpis=st.session_state.kpis, top_keywords=st.session_state.top_keywords, 
                    full_articles_data=st.session_state.full_data, brand=brand, 
                    competitors=competitors, timeframe_hours=time_range_text
                )
                st.session_state.pdf_report_bytes = pdf_bytes; pdf_generated = True
            except Exception as e: st.error(f"PDF Error: {e}")

        # 3. Excel
        with st.spinner("Building Excel..."):
            try:
                excel_data = [{'Date': i.get('date'), 'Sentiment': i.get('sentiment'), 'Text': i.get('text'), 'Link': i.get('link')} for i in st.session_state.full_data]
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: pd.DataFrame(excel_data).to_excel(writer, index=False)
                st.session_state.excel_report_bytes = output.getvalue(); excel_generated = True
            except Exception as e: st.error(f"Excel Error: {e}")

        if pdf_generated and excel_generated:
            st.session_state.report_generated = True; st.success("Reports Ready!")
            with st.expander("View Gemini Summary", expanded=True): st.markdown(st.session_state.ai_summary_text)

    # Export Buttons
    if st.session_state.get('report_generated', False):
        c_a, c_b, c_c = st.columns(3)
        with c_a: st.download_button("Download PDF", st.session_state.pdf_report_bytes, "Report.pdf", "application/pdf", use_container_width=True)
        with c_b: st.download_button("Download Excel", st.session_state.excel_report_bytes, "Mentions.xlsx", "application/xlsx", use_container_width=True)
        with c_c:
            if st.button("Email Reports", use_container_width=True):
                if recipient_email:
                    with st.spinner("Sending..."):
                        atts = [("Report.pdf", st.session_state.pdf_report_bytes, 'application/pdf'), ("Mentions.xlsx", st.session_state.excel_report_bytes, 'application/xlsx')]
                        body = f"Attached: Report for {brand}.\n\nSummary:\n{st.session_state.ai_summary_text}"
                        if servicenow_integration.send_report_email_with_attachments(recipient_email, f"Report: {brand}", body, atts): st.success("Sent!")
                        else: st.error("Email failed.")
                else: st.error("Enter email.")

def main():
    if not st.session_state.get('logged_in', False):
        st.error("Please Login."); st.page_link("app.py", label="Login", icon="🔒"); st.stop()

    lc, tc = st.columns([0.1, 0.9])
    with lc: st.image("fn logo.jpeg", width=60)
    with tc: st.title("Flash Narrative AI Dashboard")

    if 'full_data' not in st.session_state: st.session_state.full_data = []
    if 'kpis' not in st.session_state: st.session_state.kpis = {}
    if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Pending"

    with st.sidebar:
        st.image("fn logo.jpeg", width=100)
        st.header("⚙️ Settings")
        mis = st.number_input("Media Impact", value=100)
        mpi = st.number_input("Msg Penetration (%)", value=30)
        eng = st.number_input("Engagement", value=1000.0)
        rch = st.number_input("Reach", value=10000000)
        thresholds = {"mis_good": mis, "mpi_good": mpi, "eng_good": eng, "reach_good": rch}
        st.divider()
        if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

    st.subheader("Monitoring Setup")
    c1, c2, c3 = st.columns(3)
    with c1: brand = st.text_input("Brand", value="Zenith Bank")
    with c2: competitors = [x.strip() for x in st.text_input("Competitors", value="Fidelity Bank,GT Bank,Opay").split(",")]
    with c3: industry = st.selectbox("Industry", ['finance', 'tech', 'retail'])
    
    msgs = [x.strip() for x in st.text_area("Campaign Messages", value="Zecathon\nZecathon 5.0", height=70).split("\n") if x.strip()]
    tr_text = st.selectbox("Time Frame", ["Last 24 hours", "Last 7 days", "Last 30 days"])
    hours = {"Last 24 hours": 24, "Last 7 days": 168, "Last 30 days": 720}[tr_text]

    if st.button("Run Hybrid Analysis", type="primary", use_container_width=True):
        run_smart_analysis(brand, competitors, industry, msgs, hours, tr_text)

    display_dashboard(brand, competitors, tr_text, thresholds)

if __name__ == "__main__":
    main()