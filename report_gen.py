import io
import textwrap
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.colors import navy, black, gray, white, HexColor
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from collections import Counter
import os

# Import your demo loader
# --- HYBRID IMPORTS ---
try:
    from .. import gemini_integration as gemini_llm  # <--- ADD THIS
    from .. import demo_loader
except ImportError:
    import gemini_integration as gemini_llm        # <--- ADD THIS
    import demo_loader

# --- BRAND COLORS ---
GOLD = HexColor('#FFD700')
BLACK = HexColor('#000000')
BEIGE = HexColor('#F5F5DC')
DARK_BG = HexColor('#1E1E1E')
NAVY = HexColor('#003366')
LIGHT_GRAY = HexColor('#F8F9FA')
FOOTER_BG = HexColor('#2C2C2C')

def draw_watermark(c, width, height, logo_path="fn text.jpeg"):
    """Draw a subtle watermark in the center of the page"""
    try:
        if os.path.exists(logo_path):
            # Calculate center position
            watermark_width = width * 0.5
            watermark_height = height * 0.4
            x = (width - watermark_width) / 2
            y = (height - watermark_height) / 2
            
            # Draw with very low opacity
            c.saveState()
            c.setFillAlpha(0.03)  # Very subtle watermark
            c.drawImage(logo_path, x, y, 
                       width=watermark_width, 
                       height=watermark_height,
                       preserveAspectRatio=True,
                       mask='auto')
            c.restoreState()
    except Exception as e:
        print(f"Could not load watermark: {e}")

def draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on, logo_path="fn logo.jpeg"):
    """Draw professional header and footer with logo and colored background"""
    margin_x = 50
    
    # --- HEADER SECTION ---
    # Gold line at top
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.line(0, height - 35, width, height - 35)
    
    # Try to add logo in header (top left)
    try:
        if os.path.exists(logo_path):
            logo_size = 25
            c.drawImage(logo_path, margin_x, height - 32, 
                       width=logo_size, height=logo_size,
                       preserveAspectRatio=True, mask='auto')
            text_start_x = margin_x + logo_size + 10
        else:
            text_start_x = margin_x
    except Exception as e:
        print(f"Could not load logo: {e}")
        text_start_x = margin_x
    
    # Brand name in header
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(NAVY)
    c.drawString(text_start_x, height - 20, f"Flash Narrative Report: {brand}")
    
    # Date in header (right aligned)
    c.setFont("Helvetica", 8)
    c.setFillColor(gray)
    date_text = f"Generated: {generated_on}"
    date_width = c.stringWidth(date_text, "Helvetica", 8)
    c.drawString(width - margin_x - date_width, height - 20, date_text)
    
    # --- FOOTER SECTION ---
    # Dark background for footer
    c.setFillColor(FOOTER_BG)
    c.rect(0, 0, width, 50, fill=1, stroke=0)
    
    # Gold line at top of footer
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(0, 50, width, 50)
    
    # Page number (center) - in white for contrast
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GOLD)
    page_text = f"Page {page_num} of {total_pages}"
    page_width = c.stringWidth(page_text, "Helvetica-Bold", 9)
    c.drawString((width - page_width) / 2, 28, page_text)
    
    # Confidential notice (left) - in beige
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(BEIGE)
    c.drawString(margin_x, 28, "Confidential - Internal Use Only")
    
    # Powered by Flash Narrative (right)
    c.setFont("Helvetica", 7)
    c.setFillColor(BEIGE)
    powered_text = "Powered by Flash Narrative AI"
    powered_width = c.stringWidth(powered_text, "Helvetica", 7)
    c.drawString(width - margin_x - powered_width, 28, powered_text)

def draw_cover_page(c, width, height, brand, timeframe, generated_on, kpis, logo_path="fn full.jpeg"):
    """Draw an executive cover page with logo and watermark"""
    margin_x = 50
    
    # Draw watermark first (behind everything)
    draw_watermark(c, width, height)
    
    # Try to add full logo at top
    y = height - 100
    try:
        if os.path.exists(logo_path):
            logo_width = 200
            logo_height = 80
            logo_x = (width - logo_width) / 2
            c.drawImage(logo_path, logo_x, y, 
                       width=logo_width, height=logo_height,
                       preserveAspectRatio=True, mask='auto')
            y -= (logo_height + 40)
        else:
            # Fallback to text
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(NAVY)
            title_text = "Flash Narrative"
            title_width = c.stringWidth(title_text, "Helvetica-Bold", 28)
            c.drawString((width - title_width) / 2, y, title_text)
            y -= 40
    except Exception as e:
        print(f"Could not load cover logo: {e}")
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(NAVY)
        title_text = "Flash Narrative"
        title_width = c.stringWidth(title_text, "Helvetica-Bold", 28)
        c.drawString((width - title_width) / 2, y, title_text)
        y -= 40
    
    # Subtitle
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(GOLD)
    subtitle = "PR Intelligence Report"
    subtitle_width = c.stringWidth(subtitle, "Helvetica-Bold", 22)
    c.drawString((width - subtitle_width) / 2, y, subtitle)
    
    # Brand name (centered)
    y -= 60
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(black)
    brand_width = c.stringWidth(brand, "Helvetica-Bold", 20)
    c.drawString((width - brand_width) / 2, y, brand)
    
    # Analysis period
    y -= 35
    c.setFont("Helvetica", 12)
    c.setFillColor(gray)
    period_text = f"Analysis Period: {timeframe}"
    period_width = c.stringWidth(period_text, "Helvetica", 12)
    c.drawString((width - period_width) / 2, y, period_text)
    
    # Generated date
    y -= 22
    gen_text = f"Report Generated: {generated_on}"
    gen_width = c.stringWidth(gen_text, "Helvetica", 12)
    c.drawString((width - gen_width) / 2, y, gen_text)
    
    # Executive Summary Box
    y -= 70
    box_height = 220
    box_y = y - box_height
    box_width = width - 2 * margin_x
    
    # Shadow effect
    c.setFillColor(HexColor('#CCCCCC'))
    c.roundRect(margin_x + 3, box_y - 3, box_width, box_height, 12, fill=1, stroke=0)
    
    # Main box background
    c.setFillColor(LIGHT_GRAY)
    c.roundRect(margin_x, box_y, box_width, box_height, 12, fill=1, stroke=0)
    
    # Gold border
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.roundRect(margin_x, box_y, box_width, box_height, 12, fill=0, stroke=1)
    
    # Executive Summary Title
    y -= 15
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(NAVY)
    title = "Executive Summary - Key Performance Indicators"
    title_width = c.stringWidth(title, "Helvetica-Bold", 14)
    c.drawString((width - title_width) / 2, y, title)
    
    # KPI Grid (2x2)
    y -= 45
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(black)
    
    kpi_data = [
        ("Media Impact Score", f"{kpis.get('mis', 0):.0f}", GOLD),
        ("Message Penetration", f"{kpis.get('mpi', 0):.1f}%", HexColor('#4A90E2')),
        ("Avg. Engagement", f"{kpis.get('engagement_rate', 0):.1f}", HexColor('#28a745')),
        ("Total Reach", f"{kpis.get('reach', 0):,}", HexColor('#E74C3C'))
    ]
    
    col_width = (box_width - 60) / 2
    row_height = 65
    
    for i, (label, value, color) in enumerate(kpi_data):
        col = i % 2
        row = i // 2
        
        x = margin_x + 30 + (col * (col_width + 20))
        current_y = y - (row * (row_height + 10))
        
        # Mini box for each KPI
        mini_box_width = col_width - 20
        mini_box_height = 50
        
        # Colored top bar
        c.setFillColor(color)
        c.rect(x, current_y - 5, mini_box_width, 8, fill=1, stroke=0)
        
        # Label
        c.setFont("Helvetica", 9)
        c.setFillColor(gray)
        c.drawString(x + 5, current_y - 22, label)
        
        # Value
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(color)
        c.drawString(x + 5, current_y - 45, value)
    
    # Footer note
    y = box_y + 25
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(gray)
    footer_text = "This report provides AI-powered insights into brand reputation, competitive positioning, and media performance."
    footer_lines = textwrap.wrap(footer_text, width=95)
    for i, line in enumerate(footer_lines):
        line_width = c.stringWidth(line, "Helvetica-Oblique", 8)
        c.drawString((width - line_width) / 2, y - (i * 12), line)

def create_enhanced_sentiment_pie(sentiment_ratio):
    """Creates a professional doughnut chart with better styling"""
    labels, sizes, colors = [], [], []
    color_map = {
        'positive': '#28a745', 'appreciation': '#007bff', 'neutral': '#6c757d',
        'mixed': '#ffc107', 'negative': '#dc3545', 'anger': '#8b0000'
    }
    sentiment_order = ['positive', 'appreciation', 'neutral', 'mixed', 'negative', 'anger']
    
    for tone in sentiment_order:
        val = float(sentiment_ratio.get(tone, 0))
        if val > 0.1:
            labels.append(f"{tone.capitalize()}\n{val:.1f}%")
            sizes.append(val)
            colors.append(color_map.get(tone, 'grey'))
    
    if not sizes:
        labels = ['Neutral\n100.0%']
        sizes = [100.0]
        colors = ['#6c757d']
    
    # Create figure with better styling
    fig, ax = plt.subplots(figsize=(5, 5), facecolor='white')
    
    # Create doughnut with explode effect for largest segment
    explode = [0.05 if s == max(sizes) else 0 for s in sizes]
    
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='',
        startangle=90,
        pctdistance=0.85,
        explode=explode,
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
        textprops=dict(size=9, weight='bold')
    )
    
    ax.axis('equal')
    plt.title('Sentiment Distribution', fontsize=12, fontweight='bold', pad=20, color='#003366')
    
    # Save with transparent background
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf

def create_enhanced_sov_chart(all_brands, sov_values):
    """Creates a professional horizontal bar chart with better styling"""
    if not all_brands or not sov_values:
        return None
    
    try:
        # Create DataFrame and sort
        df = pd.DataFrame({'Brand': all_brands, 'SOV': sov_values}).sort_values(by='SOV', ascending=True)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(7, max(3, len(all_brands) * 0.6)), facecolor='white')
        
        # Create bars with gradient effect (highlight top brand)
        colors = ['#FFD700' if sov == max(sov_values) else '#4A90E2' for sov in df['SOV']]
        bars = ax.barh(df['Brand'], df['SOV'], color=colors, edgecolor='gray', linewidth=0.5)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{width:.1f}%', va='center', ha='left', fontsize=10, fontweight='bold')
        
        # Styling
        ax.set_xlabel('Share of Voice (%)', fontsize=10, fontweight='bold')
        ax.set_title('Competitive Share of Voice Analysis', fontsize=12, fontweight='bold', pad=15, color='#003366')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # Save
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Error creating SOV chart: {e}")
        return None

def draw_kpi_boxes(c, y, margin_x, kpis, width):
    """Draw colorful KPI boxes for visual appeal"""
    box_width = (width - 2 * margin_x - 30) / 3
    box_height = 70
    
    kpi_items = [
        ("MIS", f"{kpis.get('mis', 0):.0f}", GOLD),
        ("MPI", f"{kpis.get('mpi', 0):.1f}%", HexColor('#4A90E2')),
        ("Reach", f"{kpis.get('reach', 0):,}", HexColor('#28a745'))
    ]
    
    for i, (label, value, color) in enumerate(kpi_items):
        x = margin_x + (i * (box_width + 15))
        
        # Draw box shadow
        c.setFillColor(HexColor('#E8E8E8'))
        c.roundRect(x + 2, y - box_height - 2, box_width, box_height, 5, fill=1, stroke=0)
        
        # Draw main box
        c.setFillColor(white)
        c.roundRect(x, y - box_height, box_width, box_height, 5, fill=1, stroke=0)
        
        # Draw colored top bar
        c.setFillColor(color)
        c.roundRect(x, y - box_height, box_width, 15, 5, fill=1, stroke=0)
        
        # Label
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(white)
        label_width = c.stringWidth(label, "Helvetica-Bold", 9)
        c.drawString(x + (box_width - label_width) / 2, y - box_height + 5, label)
        
        # Value
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(color)
        value_width = c.stringWidth(value, "Helvetica-Bold", 18)
        c.drawString(x + (box_width - value_width) / 2, y - box_height + 35, value)
    
    return y - box_height - 20

def draw_section_header(c, y, margin_x, title, width):
    """Draw a professional section header with gold underline"""
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(NAVY)
    c.drawString(margin_x, y, title)
    
    # Gold underline
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(margin_x, y - 5, margin_x + c.stringWidth(title, "Helvetica-Bold", 14) + 20, y - 5)
    
    return y - 25

def draw_enhanced_mentions(c, y, title, mentions, width, margin_x, height, max_mentions=8):
    """Draw mentions with clickable sources, dates, and better visual hierarchy"""
    if y < 150:
        c.showPage()
        draw_watermark(c, width, height)
        y = height - 80
    
    y = draw_section_header(c, y, margin_x, title, width)
    
    mention_count = 0
    for item in mentions:
        if mention_count >= max_mentions:
            break
        
        headline = item.get('text', 'No Headline')[:180]
        source = item.get('source', 'Unknown Source')
        link = item.get('link', '')
        sentiment = item.get('sentiment', 'neutral')
        
        # Try to get date
        date_published = item.get('date', item.get('published', ''))
        if date_published:
            try:
                if isinstance(date_published, str):
                    # Try to parse and format date
                    from dateutil import parser as dateparser
                    parsed_date = dateparser.parse(date_published)
                    date_str = parsed_date.strftime("%b %d, %Y")
                else:
                    date_str = str(date_published)
            except:
                date_str = str(date_published)[:10]
        else:
            date_str = ""
        
        # Estimate space needed
        headline_lines = textwrap.wrap(headline, width=85)
        needed_space = len(headline_lines) * 14 + 55
        
        if y < needed_space + 80:
            c.showPage()
            draw_watermark(c, width, height)
            y = height - 80
            y = draw_section_header(c, y, margin_x, title + " (continued)", width)
        
        # Sentiment badge (top left)
        sentiment_colors = {
            'positive': HexColor('#28a745'),
            'negative': HexColor('#dc3545'),
            'anger': HexColor('#8b0000'),
            'appreciation': HexColor('#007bff'),
            'neutral': gray,
            'mixed': HexColor('#ffc107')
        }
        badge_color = sentiment_colors.get(sentiment, gray)
        
        badge_width = 75
        badge_height = 16
        c.setFillColor(badge_color)
        c.roundRect(margin_x, y - badge_height, badge_width, badge_height, 3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(white)
        badge_text = sentiment.upper()
        badge_text_width = c.stringWidth(badge_text, "Helvetica-Bold", 8)
        c.drawString(margin_x + (badge_width - badge_text_width) / 2, y - 11, badge_text)
        
        # Date badge (if available) - next to sentiment
        if date_str:
            date_badge_x = margin_x + badge_width + 5
            date_badge_width = 90
            c.setFillColor(HexColor('#6c757d'))
            c.roundRect(date_badge_x, y - badge_height, date_badge_width, badge_height, 3, fill=1, stroke=0)
            c.setFont("Helvetica", 7)
            c.setFillColor(white)
            date_text_width = c.stringWidth(date_str, "Helvetica", 7)
            c.drawString(date_badge_x + (date_badge_width - date_text_width) / 2, y - 10, date_str)
        
        # Headline
        y -= 32
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(black)
        for line in headline_lines:
            if y < 80:
                c.showPage()
                draw_watermark(c, width, height)
                y = height - 80
            c.drawString(margin_x, y, line)
            y -= 13
        
        # Source with clickable link
        y -= 5
        c.setFont("Helvetica", 8)
        c.setFillColor(gray)
        source_label = "Source: "
        c.drawString(margin_x, y, source_label)
        
        # Make source name clickable if link exists
        source_x = margin_x + c.stringWidth(source_label, "Helvetica", 8)
        
        if link and str(link).strip() and str(link).startswith('http'):
            # Clickable link
            c.setFillColor(HexColor('#007bff'))
            c.setFont("Helvetica", 8)
            c.drawString(source_x, y, source)
            
            # Underline
            source_width = c.stringWidth(source, "Helvetica", 8)
            c.setStrokeColor(HexColor('#007bff'))
            c.setLineWidth(0.5)
            c.line(source_x, y - 1, source_x + source_width, y - 1)
            
            # Add link annotation
            try:
                link_rect = (source_x, y - 2, source_x + source_width, y + 10)
                c.linkURL(str(link).strip(), link_rect, relative=0)
            except Exception as link_e:
                print(f"Could not create link for {source}: {link_e}")
        else:
            # Non-clickable
            c.setFillColor(gray)
            c.drawString(source_x, y, source)
        
        y -= 18
        
        # Separator line
        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.line(margin_x, y, width - margin_x, y)
        y -= 15
        
        mention_count += 1
    
    if mention_count == 0:
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(gray)
        c.drawString(margin_x, y, "No mentions found in this category.")
        y -= 25
    
    return y

def draw_styled_table(c, y, margin_x, width, data, col_widths=None):
    """Draw a professionally styled table with alternating row colors"""
    if not data or len(data) < 2:
        return y
    
    num_cols = len(data[0])
    if col_widths is None:
        col_widths = [(width - 2 * margin_x) / num_cols] * num_cols
    
    row_height = 25
    
    # Header row with navy background
    c.setFillColor(NAVY)
    c.rect(margin_x, y - row_height, sum(col_widths), row_height, fill=1, stroke=0)
    
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(white)
    x_pos = margin_x + 10
    for i, cell in enumerate(data[0]):
        c.drawString(x_pos, y - row_height + 8, str(cell))
        x_pos += col_widths[i]
    
    y -= row_height
    
    # Data rows with alternating colors
    c.setFont("Helvetica", 9)
    for row_idx, row in enumerate(data[1:], 1):
        # Alternating row colors
        if row_idx % 2 == 0:
            c.setFillColor(LIGHT_GRAY)
            c.rect(margin_x, y - row_height, sum(col_widths), row_height, fill=1, stroke=0)
        
        c.setFillColor(black)
        x_pos = margin_x + 10
        for i, cell in enumerate(row):
            cell_text = str(cell)
            if len(cell_text) > 50:  # Wrap long text
                cell_text = cell_text[:47] + "..."
            c.drawString(x_pos, y - row_height + 8, cell_text)
            x_pos += col_widths[i]
        
        y -= row_height
    
    return y - 10

def generate_report(kpis, top_keywords, full_articles_data, brand="Brand", competitors=None, timeframe_hours=24, include_json=False):
    """Enhanced report generation with watermarks, logos, and professional styling"""
    if competitors is None:
        competitors = []
    
    # Categorize mentions
    main_brand_mentions = []
    competitor_mentions = []
    related_mentions = []
    
    lower_brand = brand.lower()
    lower_competitors = {c.lower() for c in competitors}
    
    for item in full_articles_data:
        mentioned_brands_lower = set()
        mentioned_str = item.get('mentioned_brands', '')
        if isinstance(mentioned_str, str):
            mentioned_brands_lower = {b.strip().lower() for b in mentioned_str.split(',') if b.strip()}
        elif isinstance(mentioned_str, list):
            mentioned_brands_lower = {b.strip().lower() for b in mentioned_str}
        
        mentions_main = lower_brand in mentioned_brands_lower
        mentions_comp = any(comp in mentioned_brands_lower for comp in lower_competitors)
        
        if mentions_main and not mentions_comp:
            main_brand_mentions.append(item)
        elif not mentions_main and mentions_comp:
            competitor_mentions.append(item)
        else:
            related_mentions.append(item)
    
    # Get KPI data
    sentiment_ratio = kpis.get('sentiment_ratio', {})
    sov = kpis.get('sov', [])
    all_brands = kpis.get('all_brands', [brand] + competitors)
    generated_on = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    if isinstance(timeframe_hours, int):
        time_text = f"Last {timeframe_hours} Hours"
    else:
        time_text = timeframe_hours
    
    # Load AI Summary
    # --- LOAD AI SUMMARY (HYBRID LOGIC) ---
    ai_summary = ""
    try:
        # 1. Attempt Live Generation via Gemini
        # We pass the data context to the LLM here
        ai_summary = gemini_llm.generate_llm_report_summary(
            kpis, top_keywords, full_articles_data, brand, competitors
        )
    except Exception as e:
        # 2. Fallback to Demo Text if Gemini/Internet fails
        print(f"ReportGen: Gemini failed ({e}). Using Demo Fallback.")
        try:
            ai_summary = demo_loader.load_ai_summary()
        except:
            ai_summary = "Executive Summary unavailable at this time."
    
    # Create PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter
    margin_x = 50
    
    # Estimate total pages
    total_pages = 15
    
    # === PAGE 1: COVER PAGE ===
    draw_cover_page(c, width, height, brand, time_text, generated_on, kpis)
    c.showPage()
    
    # === PAGE 2+: CONTENT PAGES ===
    page_num = 2
    
    # Performance Dashboard
    draw_watermark(c, width, height)
    draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
    y = height - 80
    y = draw_section_header(c, y, margin_x, "Performance Dashboard", width)
    y = draw_kpi_boxes(c, y, margin_x, kpis, width)
    
    # Sentiment Chart
    pie_buf = create_enhanced_sentiment_pie(sentiment_ratio)
    if pie_buf:
        try:
            img = ImageReader(pie_buf)
            img_width = 250
            img_height = 250
            img_x = margin_x
            if y < img_height + 80:
                c.showPage()
                page_num += 1
                draw_watermark(c, width, height)
                draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                y = height - 80
            y -= img_height
            c.drawImage(img, img_x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error drawing sentiment chart: {e}")
    
    # SOV Chart (next to sentiment if space)
    sov_buf = create_enhanced_sov_chart(all_brands, sov)
    if sov_buf:
        try:
            img_sov = ImageReader(sov_buf)
            img_width = 300
            img_height = 200
            img_x = width - margin_x - img_width
            img_y = y + 25
            c.drawImage(img_sov, img_x, img_y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error drawing SOV chart: {e}")
    
    y -= 40
    
    # === AI SUMMARY SECTION ===
    if y < 200:
        c.showPage()
        page_num += 1
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
        y = height - 80
    
    y = draw_section_header(c, y, margin_x, "AI-Powered Insights & Recommendations", width)
    
    # Parse and draw AI summary with improved formatting
    ai_lines = ai_summary.split('\n')
    i = 0
    while i < len(ai_lines):
        r = ai_lines[i].rstrip()
        
        if not r:  # Skip empty lines
            y -= 6
            if y < 80:
                c.showPage()
                page_num += 1
                draw_watermark(c, width, height)
                draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                y = height - 80
            i += 1
            continue
        
        # Horizontal rule
        if r in ['---', '***', '___']:
            c.setStrokeColor(GOLD)
            c.setLineWidth(1)
            c.line(margin_x, y - 5, width - margin_x, y - 5)
            y -= 12
            if y < 80:
                c.showPage()
                page_num += 1
                draw_watermark(c, width, height)
                draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                y = height - 80
            i += 1
            continue
        
        # Table detection
        if r.startswith('|'):
            table_lines = []
            while i < len(ai_lines) and ai_lines[i].strip().startswith('|'):
                table_lines.append(ai_lines[i].strip())
                i += 1
            i -= 1
            
            rows = []
            for line in table_lines:
                if '---' in line and all('-' in cell or '|' in cell for cell in line.split('|')):
                    continue
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                rows.append(cells)
            
            if rows:
                num_cols = max(len(row) for row in rows)
                cell_width = (width - 2 * margin_x - 20) / num_cols
                row_height = 20
                
                table_height = len(rows) * row_height + 30
                if y < table_height + 80:
                    c.showPage()
                    page_num += 1
                    draw_watermark(c, width, height)
                    draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                    y = height - 80
                
                # Header row
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(NAVY)
                c.rect(margin_x, y - row_height, width - 2 * margin_x, row_height, fill=0, stroke=1)
                for j, cell in enumerate(rows[0]):
                    cell = cell.replace('**', '')
                    wrapped = textwrap.wrap(cell, width=int(cell_width / 6))
                    for k, wline in enumerate(wrapped):
                        c.drawString(margin_x + 5 + j * cell_width, y - row_height + 12 - k * 10, wline)
                y -= row_height
                
                # Data rows
                c.setFont("Helvetica", 8)
                c.setFillColor(black)
                for row_idx, row in enumerate(rows[1:], 1):
                    if row_idx % 2 == 0:
                        c.setFillColor(LIGHT_GRAY)
                        c.rect(margin_x, y - row_height, width - 2 * margin_x, row_height, fill=1, stroke=0)
                        c.setFillColor(black)
                    else:
                        c.rect(margin_x, y - row_height, width - 2 * margin_x, row_height, fill=0, stroke=1)
                    
                    for j, cell in enumerate(row):
                        cell = cell.replace('**', '').strip()
                        wrapped = textwrap.wrap(cell, width=int(cell_width / 6))
                        for k, wline in enumerate(wrapped):
                            if y - k * 10 < 80:
                                c.showPage()
                                page_num += 1
                                draw_watermark(c, width, height)
                                draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                                y = height - 80
                            c.drawString(margin_x + 5 + j * cell_width, y - row_height + 12 - k * 10, wline)
                    y -= row_height
                y -= 10
            i += 1
            continue
        
        # Header detection
        font_size = 10
        font = "Helvetica"
        is_header = False
        
        if r.startswith('### '):
            font = "Helvetica-Bold"
            font_size = 11
            r = r[4:].strip()
            is_header = True
            c.setFillColor(NAVY)
        elif r.startswith('## '):
            font = "Helvetica-Bold"
            font_size = 12
            r = r[3:].strip()
            is_header = True
            c.setFillColor(NAVY)
        elif r.startswith('# '):
            font = "Helvetica-Bold"
            font_size = 14
            r = r[2:].strip()
            is_header = True
            c.setFillColor(NAVY)
        else:
            c.setFillColor(black)
        
        # Bold text
        if r.startswith('**') and r.endswith('**'):
            r = r[2:-2].strip()
            font = "Helvetica-Bold"
        
        # Bullets
        is_bullet = r.startswith('* ') or r.startswith('- ')
        if is_bullet:
            r = r[2:].strip()
            if r.startswith('**') and r.endswith('**'):
                r = r[2:-2].strip()
                font = "Helvetica-Bold"
        
        c.setFont(font, font_size)
        
        # Wrap and draw
        wrap_width = 80 if is_bullet else 90
        lines = textwrap.wrap(r, width=wrap_width)
        for j, line in enumerate(lines):
            if y < 80:
                c.showPage()
                page_num += 1
                draw_watermark(c, width, height)
                draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
                y = height - 80
                c.setFont(font, font_size)
                if is_header:
                    c.setFillColor(NAVY)
                else:
                    c.setFillColor(black)
            
            draw_x = margin_x + (15 if is_bullet else 0)
            draw_string = line
            if is_bullet and j == 0:
                draw_string = f"• {line}"
            c.drawString(draw_x, y, draw_string)
            y -= 12 + (2 if is_header else 0)
        
        if is_header:
            y -= 5
        
        i += 1
    
    y -= 15
    
    # === MENTIONS SECTIONS ===
    if y < height / 2:
        c.showPage()
        page_num += 1
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
        y = height - 80
    
    y = draw_enhanced_mentions(c, y, f"{brand} Media Coverage", main_brand_mentions, width, margin_x, height)
    
    if y < 200:
        c.showPage()
        page_num += 1
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
        y = height - 80
    
    y = draw_enhanced_mentions(c, y, "Competitive Intelligence", competitor_mentions, width, margin_x, height)
    
    if y < 200:
        c.showPage()
        page_num += 1
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
        y = height - 80
    
    y = draw_enhanced_mentions(c, y, "Related News & Passive Mentions", related_mentions, width, margin_x, height)
    
    # === KEYWORDS SECTION ===
    if y < 250:
        c.showPage()
        page_num += 1
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num, total_pages, generated_on)
        y = height - 80
    
    y = draw_section_header(c, y, margin_x, "Trending Keywords & Phrases", width)
    
    # Create keyword table
    kw_data = [["Keyword / Phrase", "Frequency"]]
    for word, freq in top_keywords[:20]:
        kw_data.append([word, str(freq)])
    
    y = draw_styled_table(c, y, margin_x, width, kw_data, col_widths=[400, 112])
    
    # === FINALIZE PDF ===
    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    # === MARKDOWN GENERATION ===
    md_lines = [
        f"# Flash Narrative Report: {brand}",
        f"**Period:** {time_text}",
        f"**Generated:** {generated_on}",
        "",
        "## Key Performance Indicators",
        f"- **Media Impact Score (MIS):** {kpis.get('mis', 0):.0f}",
        f"- **Message Penetration (MPI):** {kpis.get('mpi', 0):.1f}%",
        f"- **Avg. Social Engagement:** {kpis.get('engagement_rate', 0):.1f}",
        f"- **Total Reach:** {kpis.get('reach', 0):,}",
        "",
        "## Sentiment Distribution",
    ]
    
    for tone, val in sentiment_ratio.items():
        md_lines.append(f"- **{tone.capitalize()}:** {val:.1f}%")
    
    md_lines.append("\n## Share of Voice (SOV)")
    md_lines.append("| Brand | SOV (%) |")
    md_lines.append("|-------|---------|")
    
    if len(sov) < len(all_brands):
        sov += [0] * (len(all_brands) - len(sov))
    
    for b, s in zip(all_brands, sov):
        md_lines.append(f"| {b} | {s:.1f} |")
    
    md_lines.append("\n## AI Summary")
    md_lines.append(ai_summary)
    
    md = "\n".join(md_lines)
    
    # === JSON SUMMARY ===
    json_summary = {
        "brand": brand,
        "competitors": competitors,
        "kpis": kpis,
        "top_keywords": top_keywords,
        "generated_on": generated_on,
        "ai_summary": ai_summary[:500] + "..." if len(ai_summary) > 500 else ai_summary
    }
    
    if include_json:
        return md, pdf_bytes, json_summary
    return md, pdf_bytes

# def render_ai_summary(c, y, margin_x, width, height, ai_summary, brand, page_num_ref, total_pages, generated_on):
    """
    Render AI summary with better markdown handling.
    - Tries to use 'markdown' package to convert to HTML and render via Paragraph.
    - Falls back to simple paragraph-by-paragraph rendering with basic bold/links handling.
    - page_num_ref is a dict-like mutable container {'page': current_page} so caller can increment it.
    Returns updated y and updated page number inside page_num_ref.
    """
    # Normalize whitespace and line endings
    text = ai_summary.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\t', '    ')
    # Pre-scan for simple markdown tables and render them using existing draw_styled_table
    lines = text.split('\n')
    i = 0
    try:
        import markdown
        md_available = True
    except Exception:
        md_available = False

    styles = getSampleStyleSheet()
    p_style = ParagraphStyle('ai_par', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=black)
    h_style = ParagraphStyle('ai_h', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=NAVY)

    def new_page():
        page_num_ref['page'] += 1
        c.showPage()
        draw_watermark(c, width, height)
        draw_header_footer(c, width, height, brand, page_num_ref['page'], total_pages, generated_on)
        return height - 80

    while i < len(lines):
        # Detect table block (markdown table starting with |)
        if lines[i].strip().startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            # parse table into rows
            rows = []
            for tl in table_lines:
                # skip separator row like |---|---|
                if set(tl.replace('|', '').strip()) <= set('-: '):
                    continue
                cells = [c.strip() for c in tl.strip('|').split('|')]
                rows.append(cells)
            if rows:
                # Ensure enough vertical space
                est_height = max(100, 20 * len(rows))
                if y < est_height + 80:
                    y = new_page()
                # Use existing draw_styled_table (it requires a header + rows)
                try:
                    y = draw_styled_table(c, y, margin_x, width, rows)
                except Exception as e:
                    # fallback: draw simple lines
                    for r in rows:
                        if y < 120:
                            y = new_page()
                        c.setFont("Helvetica", 9)
                        c.setFillColor(black)
                        c.drawString(margin_x, y, " | ".join(r))
                        y -= 14
            continue

        # Collect a paragraph (split by blank line)
        para_lines = []
        while i < len(lines) and lines[i].strip() != '':
            para_lines.append(lines[i])
            i += 1
        # skip blank lines
        while i < len(lines) and lines[i].strip() == '':
            i += 1
        para = '\n'.join(para_lines).strip()
        if not para:
            continue

        # If markdown available, convert this paragraph to HTML and then to a Paragraph
        if md_available:
            try:
                html = markdown.markdown(para, extensions=['extra'])
                # Basic handling: strip outer <p> tags if present
                # Convert some tags unsupported by Paragraph if necessary
                # Create Paragraph and measure
                p = Paragraph(html, p_style)
                w, h = p.wrap(width - 2 * margin_x, y)
                if y - h < 80:
                    y = new_page()
                p.drawOn(c, margin_x, y - h)
                y -= (h + 8)
                continue
            except Exception as e:
                # fallback to simple render below
                pass

        # Fallback simple formatting: inline bold **text**, links [text](url)
        # Convert bold -> <b>, italic -> <i>, links -> <a href="">
        simple = para
        # bold
        import re
        simple = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', simple)
        # italic
        simple = re.sub(r'\*(.+?)\*', r'<i>\1</i>', simple)
        # links
        simple = re.sub(r'\[([^\]]+)\]\((http[^\)]+)\)', r'<a href="\2">\1</a>', simple)

        # Heading detection
        if simple.startswith('# '):
            text_val = simple[2:].strip()
            p = Paragraph(f'<b>{text_val}</b>', h_style)
        elif simple.startswith('## '):
            text_val = simple[3:].strip()
            p = Paragraph(f'<b>{text_val}</b>', h_style)
        elif simple.startswith('### '):
            text_val = simple[4:].strip()
            p = Paragraph(f'<b>{text_val}</b>', h_style)
        else:
            # treat as normal paragraph
            p = Paragraph(simple.replace('\n', '<br/>'), p_style)

        w, h = p.wrap(width - 2 * margin_x, y)
        if y - h < 80:
            y = new_page()
        p.drawOn(c, margin_x, y - h)
        y -= (h + 8)

    return y, page_num_ref['page']