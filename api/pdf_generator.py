import zlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

class SimplePDFBuilder:
    """
    A pure-Python, zero-dependency PDF 1.4 document builder.
    Produces valid, clean, standards-compliant PDF documents with text,
    rectangles, badges, tables, multi-page layout, headers, and footers.
    """

    PAGE_WIDTH = 612.0   # Letter width in pt (8.5 in * 72)
    PAGE_HEIGHT = 792.0  # Letter height in pt (11 in * 72)
    MARGIN_LEFT = 40.0
    MARGIN_RIGHT = 40.0
    MARGIN_TOP = 45.0
    MARGIN_BOTTOM = 45.0

    def __init__(self, title: str = "Omiver Recommendation Report"):
        self.title = title
        self.pages: List[List[str]] = []
        self.current_page_ops: List[str] = []
        self.y = self.PAGE_HEIGHT - self.MARGIN_TOP
        self.page_number = 0
        self._start_new_page()

    @property
    def content_width(self) -> float:
        return self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT

    def _start_new_page(self):
        if self.current_page_ops:
            self.pages.append(self.current_page_ops)
        self.current_page_ops = []
        self.page_number += 1
        self.y = self.PAGE_HEIGHT - self.MARGIN_TOP

        # Draw page running header if not page 1
        if self.page_number > 1:
            self._draw_running_header()

    def _draw_running_header(self):
        y = self.PAGE_HEIGHT - 30
        self.draw_rect(self.MARGIN_LEFT, y - 5, self.content_width, 1, fill_color=(0.85, 0.88, 0.90))
        self.draw_text("OMIVER PRECISION HEALTH • PERSONALIZED RECOMMENDATIONS", 
                        self.MARGIN_LEFT, y, font="Helvetica-Bold", size=8, color=(0.4, 0.45, 0.5))
        self.y = self.PAGE_HEIGHT - self.MARGIN_TOP - 10

    def ensure_space(self, height_needed: float):
        """If there isn't enough vertical space on the current page, create a new one."""
        if self.y - height_needed < self.MARGIN_BOTTOM:
            self._start_new_page()

    def set_fill_color(self, r: float, g: float, b: float):
        self.current_page_ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke_color(self, r: float, g: float, b: float):
        self.current_page_ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def draw_rect(self, x: float, y: float, w: float, h: float, 
                  fill_color: Optional[tuple] = None, 
                  stroke_color: Optional[tuple] = None, 
                  line_width: float = 1.0):
        ops = []
        if fill_color:
            ops.append(f"{fill_color[0]:.3f} {fill_color[1]:.3f} {fill_color[2]:.3f} rg")
        if stroke_color:
            ops.append(f"{stroke_color[0]:.3f} {stroke_color[1]:.3f} {stroke_color[2]:.3f} RG")
            ops.append(f"{line_width:.2f} w")
        
        ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        
        if fill_color and stroke_color:
            ops.append("B")
        elif fill_color:
            ops.append("f")
        elif stroke_color:
            ops.append("S")
        else:
            ops.append("n")
            
        self.current_page_ops.append("\n".join(ops))

    def _escape_text(self, text: str) -> str:
        text = str(text or "")
        # Remove non-ASCII characters or map them to safe equivalents
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        # Replace common unicode dashes and quotes
        text = (text.replace("—", " - ")
                    .replace("–", " - ")
                    .replace("“", '"')
                    .replace("”", '"')
                    .replace("‘", "'")
                    .replace("’", "'")
                    .replace("•", "*")
                    .replace("…", "..."))
        # Filter to latin-1 / printable characters
        return "".join(c if 32 <= ord(c) <= 126 or 160 <= ord(c) <= 255 else " " for c in text)

    def draw_text(self, text: str, x: float, y: float, 
                  font: str = "Helvetica", size: float = 10, 
                  color: tuple = (0.1, 0.1, 0.1)):
        escaped = self._escape_text(text)
        r, g, b = color
        font_tag = "/F1"
        if "Bold" in font:
            font_tag = "/F2"
        elif "Oblique" in font or "Italic" in font:
            font_tag = "/F3"

        op = (
            f"BT\n"
            f"{font_tag} {size:.1f} Tf\n"
            f"{r:.3f} {g:.3f} {b:.3f} rg\n"
            f"1 0 0 1 {x:.2f} {y:.2f} Tm\n"
            f"({escaped}) Tj\n"
            f"ET"
        )
        self.current_page_ops.append(op)

    def wrap_text(self, text: str, max_width: float, font: str = "Helvetica", size: float = 10) -> List[str]:
        """Simple, robust word wrapping approximation for standard PDF fonts."""
        # Average char width estimation: Helvetica ~ 0.52 * font size, Bold ~ 0.58
        char_width = size * (0.58 if "Bold" in font else 0.50)
        max_chars = max(10, int(max_width / char_width))

        words = str(text or "").split()
        if not words:
            return [""]

        lines = []
        current_line = []
        current_len = 0

        for word in words:
            word_len = len(word)
            if current_line and (current_len + 1 + word_len) > max_chars:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_len = word_len
            else:
                current_line.append(word)
                current_len += (1 + word_len) if current_line else word_len

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def add_paragraph(self, text: str, font: str = "Helvetica", size: float = 9.5, 
                      color: tuple = (0.2, 0.25, 0.3), line_height: Optional[float] = None, 
                      indent: float = 0.0, space_after: float = 8.0):
        if line_height is None:
            line_height = size * 1.35

        lines = self.wrap_text(text, self.content_width - indent, font=font, size=size)
        total_height = len(lines) * line_height + space_after
        self.ensure_space(total_height)

        for line in lines:
            self.draw_text(line, self.MARGIN_LEFT + indent, self.y - size, font=font, size=size, color=color)
            self.y -= line_height

        self.y -= space_after

    def add_bullet(self, text: str, bullet_char: str = "•", 
                   font: str = "Helvetica", size: float = 9.0, 
                   color: tuple = (0.2, 0.25, 0.3), space_after: float = 4.0):
        line_height = size * 1.35
        lines = self.wrap_text(text, self.content_width - 24, font=font, size=size)
        total_height = len(lines) * line_height + space_after
        self.ensure_space(total_height)

        # Draw bullet symbol
        self.draw_text(bullet_char, self.MARGIN_LEFT + 8, self.y - size, font="Helvetica-Bold", size=size, color=(0.15, 0.45, 0.35))

        for idx, line in enumerate(lines):
            self.draw_text(line, self.MARGIN_LEFT + 22, self.y - size, font=font, size=size, color=color)
            self.y -= line_height

        self.y -= space_after

    def add_section_header(self, title: str, subtitle: Optional[str] = None, 
                           icon_text: str = "", badge_text: Optional[str] = None,
                           badge_color: tuple = (0.1, 0.45, 0.3)):
        header_height = 42 if subtitle else 32
        self.ensure_space(header_height + 15)

        y_top = self.y
        # Accent left border bar
        self.draw_rect(self.MARGIN_LEFT, y_top - 24, 4, 24, fill_color=(0.09, 0.40, 0.22))
        
        # Section title
        display_title = f"{icon_text} {title}".strip()
        self.draw_text(display_title, self.MARGIN_LEFT + 12, y_top - 18, font="Helvetica-Bold", size=13, color=(0.09, 0.25, 0.18))

        if badge_text:
            badge_width = len(badge_text) * 6.5 + 16
            bx = self.MARGIN_LEFT + self.content_width - badge_width
            self.draw_rect(bx, y_top - 20, badge_width, 18, fill_color=(0.93, 0.97, 0.94), stroke_color=badge_color, line_width=0.8)
            self.draw_text(badge_text.upper(), bx + 8, y_top - 15, font="Helvetica-Bold", size=8, color=badge_color)

        self.y -= 26

        if subtitle:
            self.draw_text(subtitle, self.MARGIN_LEFT + 12, self.y - 10, font="Helvetica-Oblique", size=9, color=(0.45, 0.5, 0.55))
            self.y -= 14

        self.y -= 8

    def add_card(self, title: str, items: List[tuple], bg_color: tuple = (0.97, 0.98, 0.99)):
        """Draws a neat rounded/bordered key-value info box."""
        row_height = 16.0
        header_height = 24.0
        padding = 10.0
        total_height = header_height + (len(items) * row_height) + (padding * 2)
        
        self.ensure_space(total_height + 10)
        
        box_y = self.y - total_height
        # Card Background & Border
        self.draw_rect(self.MARGIN_LEFT, box_y, self.content_width, total_height, 
                       fill_color=bg_color, stroke_color=(0.85, 0.88, 0.90), line_width=1.0)
        
        # Header text
        self.draw_text(title.upper(), self.MARGIN_LEFT + padding, self.y - padding - 12, 
                       font="Helvetica-Bold", size=9.5, color=(0.15, 0.35, 0.28))
        
        # Header divider
        div_y = self.y - padding - 18
        self.draw_rect(self.MARGIN_LEFT + padding, div_y, self.content_width - (padding * 2), 0.75, 
                       fill_color=(0.88, 0.90, 0.92))
        
        curr_y = div_y - 14
        for label, val in items:
            self.draw_text(f"{label}:", self.MARGIN_LEFT + padding + 4, curr_y, font="Helvetica-Bold", size=8.5, color=(0.3, 0.35, 0.4))
            val_lines = self.wrap_text(str(val or "—"), self.content_width - 150, font="Helvetica", size=8.5)
            self.draw_text(val_lines[0] if val_lines else "—", self.MARGIN_LEFT + 140, curr_y, font="Helvetica", size=8.5, color=(0.15, 0.2, 0.25))
            curr_y -= row_height
            
        self.y = box_y - 12

    def add_table(self, headers: List[str], rows: List[List[str]], col_widths: Optional[List[float]] = None):
        """Draws a clean tabular view for meal plans or biomarkers."""
        if not rows:
            return

        num_cols = len(headers)
        if not col_widths:
            equal_w = self.content_width / num_cols
            col_widths = [equal_w] * num_cols

        row_h = 24.0
        hdr_h = 22.0

        # Check space for header + at least 2 rows
        self.ensure_space(hdr_h + (row_h * min(2, len(rows))) + 15)

        # Draw Header Row
        self.draw_rect(self.MARGIN_LEFT, self.y - hdr_h, self.content_width, hdr_h, 
                       fill_color=(0.10, 0.35, 0.24))

        x_cur = self.MARGIN_LEFT
        for i, h in enumerate(headers):
            w = col_widths[i]
            self.draw_text(h.upper(), x_cur + 8, self.y - 15, font="Helvetica-Bold", size=8.5, color=(1.0, 1.0, 1.0))
            x_cur += w

        self.y -= hdr_h

        # Draw Data Rows
        for r_idx, row in enumerate(rows):
            # Compute required row height based on cell text wrapping
            max_lines = 1
            cell_lines_list = []
            for c_idx, cell in enumerate(row):
                w = col_widths[c_idx] - 12
                lines = self.wrap_text(str(cell or ""), w, font="Helvetica", size=8.0)
                max_lines = max(max_lines, len(lines))
                cell_lines_list.append(lines)

            this_row_h = max(20.0, max_lines * 12.0 + 8.0)
            self.ensure_space(this_row_h + 5)

            # Alternate row background
            bg = (0.97, 0.98, 0.99) if r_idx % 2 == 1 else (1.0, 1.0, 1.0)
            self.draw_rect(self.MARGIN_LEFT, self.y - this_row_h, self.content_width, this_row_h, 
                           fill_color=bg, stroke_color=(0.88, 0.90, 0.92), line_width=0.5)

            # Draw cell text
            x_cur = self.MARGIN_LEFT
            for c_idx, lines in enumerate(cell_lines_list):
                w = col_widths[c_idx]
                line_y = self.y - 11.0
                font_to_use = "Helvetica-Bold" if c_idx == 0 else "Helvetica"
                color_to_use = (0.1, 0.15, 0.2) if c_idx == 0 else (0.25, 0.3, 0.35)
                
                # If status column, add badge-like styling
                if "OPTIMAL" in lines[0] or "NORMAL" in lines[0]:
                    color_to_use = (0.08, 0.45, 0.2)
                elif "HIGH" in lines[0] or "LOW" in lines[0]:
                    color_to_use = (0.75, 0.2, 0.15)

                for line in lines:
                    self.draw_text(line, x_cur + 8, line_y, font=font_to_use, size=8.0, color=color_to_use)
                    line_y -= 11.0
                x_cur += w

            self.y -= this_row_h

        self.y -= 12

    def build(self) -> bytes:
        """Finalize and compile the PDF stream into raw bytes."""
        if self.current_page_ops:
            self.pages.append(self.current_page_ops)

        total_pages = len(self.pages)

        # Add page footers with actual total page count
        for p_idx, page_ops in enumerate(self.pages):
            p_num = p_idx + 1
            footer_y = 25.0
            
            # Bottom line
            rule = (f"{self.MARGIN_LEFT:.2f} {footer_y + 12:.2f} {self.content_width:.2f} 0.75 re f\n"
                    f"0.85 0.88 0.90 rg")
            page_ops.append(rule)
            
            # Footer text
            left_txt = "Confidential • Generated by Omiver Precision Health AI Platform"
            right_txt = f"Page {p_num} of {total_pages}"
            
            page_ops.append(
                f"BT\n/F1 7.5 Tf\n0.45 0.5 0.55 rg\n"
                f"1 0 0 1 {self.MARGIN_LEFT:.2f} {footer_y:.2f} Tm\n"
                f"({self._escape_text(left_txt)}) Tj\n"
                f"ET"
            )
            page_ops.append(
                f"BT\n/F2 7.5 Tf\n0.45 0.5 0.55 rg\n"
                f"1 0 0 1 {self.PAGE_WIDTH - self.MARGIN_RIGHT - 50:.2f} {footer_y:.2f} Tm\n"
                f"({self._escape_text(right_txt)}) Tj\n"
                f"ET"
            )

        # Compile PDF objects
        body: List[bytes] = []
        offsets: List[int] = []

        def add_obj(obj_bytes: bytes) -> int:
            obj_num = len(offsets) + 1
            offsets.append(sum(len(b) for b in body))
            body.append(f"{obj_num} 0 obj\n".encode("latin1") + obj_bytes + b"\nendobj\n")
            return obj_num

        # PDF Header
        body.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        # Object placeholders
        # 1: Catalog
        # 2: Pages root
        # 3..3+N: Page objects
        # Next: Content streams
        # Resources: Fonts

        catalog_num = 1
        pages_num = 2
        page_obj_nums = []

        # We will create font objects:
        font1_num = 0
        font2_num = 0
        font3_num = 0

        # Pre-assign object IDs
        cur_id = 3
        for _ in self.pages:
            page_obj_nums.append(cur_id)
            cur_id += 2  # one for Page, one for Content stream

        font1_num = cur_id
        font2_num = cur_id + 1
        font3_num = cur_id + 2
        res_num = cur_id + 3

        # Write Catalog (1)
        add_obj(f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode("latin1"))

        # Write Pages root (2)
        kids_str = " ".join(f"{num} 0 R" for num in page_obj_nums)
        add_obj(f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode("latin1"))

        # Write Pages and Streams
        for idx, page_ops in enumerate(self.pages):
            p_obj_id = page_obj_nums[idx]
            c_obj_id = p_obj_id + 1

            # Page Object
            add_obj(
                f"<< /Type /Page /Parent {pages_num} 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Contents {c_obj_id} 0 R /Resources {res_num} 0 R >>".encode("latin1")
            )

            # Content stream
            stream_content = "\n".join(page_ops).encode("latin1", errors="replace")
            compressed_stream = zlib.compress(stream_content)
            stream_obj = (
                f"<< /Length {len(compressed_stream)} /Filter /FlateDecode >>\nstream\n".encode("latin1")
                + compressed_stream
                + b"\nendstream"
            )
            add_obj(stream_obj)

        # Standard Fonts
        add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>")

        # Shared Resources Dictionary
        add_obj(
            f"<< /Font << /F1 {font1_num} 0 R /F2 {font2_num} 0 R /F3 {font3_num} 0 R >> >>".encode("latin1")
        )

        # Cross Reference Table (xref)
        xref_offset = sum(len(b) for b in body)
        xref_lines = [f"xref\n0 {len(offsets) + 1}\n0000000000 65535 f \n"]
        for off in offsets:
            xref_lines.append(f"{off:010d} 00000 n \n")

        trailer = (
            f"trailer\n"
            f"<< /Size {len(offsets) + 1} /Root {catalog_num} 0 R "
            f"/Info << /Title ({self._escape_text(self.title)}) /Creator (Omiver Health AI) >> >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        )

        return b"".join(body) + "".join(xref_lines).encode("latin1") + trailer.encode("latin1")


def generate_recommendation_pdf(recommendation) -> bytes:
    """
    Generates a comprehensive, beautifully-styled clinical PDF report from a Recommendation model instance.
    """
    client = recommendation.client
    biomarker_test = recommendation.biomarker_test

    patient_name = f"{getattr(client, 'first_name', '')} {getattr(client, 'last_name', '')}".strip()
    if not patient_name:
        patient_name = f"Client #{client.id}"

    title = f"Omiver Recommendation Plan - {patient_name}"
    pdf = SimplePDFBuilder(title=title)

    # 1. Main Header Banner
    header_box_h = 75.0
    pdf.draw_rect(pdf.MARGIN_LEFT, pdf.y - header_box_h, pdf.content_width, header_box_h, 
                  fill_color=(0.09, 0.38, 0.22))
    
    pdf.draw_text("OMIVER PRECISION HEALTH", pdf.MARGIN_LEFT + 16, pdf.y - 24, 
                  font="Helvetica-Bold", size=16, color=(1.0, 1.0, 1.0))
    pdf.draw_text("METABOLIC & LIFESTYLE INTERVENTION REPORT", pdf.MARGIN_LEFT + 16, pdf.y - 42, 
                  font="Helvetica", size=10, color=(0.85, 0.94, 0.88))
    
    # Sub-info on right side of banner
    created_str = recommendation.created_at.strftime("%B %d, %Y") if recommendation.created_at else datetime.now().strftime("%B %d, %Y")
    rec_id_str = f"Plan ID: REC-{recommendation.id:05d}"
    pdf.draw_text(rec_id_str, pdf.PAGE_WIDTH - pdf.MARGIN_RIGHT - 130, pdf.y - 24, 
                  font="Helvetica-Bold", size=9, color=(1.0, 1.0, 1.0))
    pdf.draw_text(f"Date: {created_str}", pdf.PAGE_WIDTH - pdf.MARGIN_RIGHT - 130, pdf.y - 40, 
                  font="Helvetica", size=8.5, color=(0.85, 0.94, 0.88))
    
    status_label = recommendation.status or "DRAFT"
    pdf.draw_text(f"Status: {status_label}", pdf.PAGE_WIDTH - pdf.MARGIN_RIGHT - 130, pdf.y - 56, 
                  font="Helvetica-Bold", size=8.5, color=(0.95, 0.90, 0.60) if status_label != "APPROVED" else (0.7, 1.0, 0.7))

    pdf.y -= (header_box_h + 16)

    # 2. Patient & Clinical Profile Card
    dob_val = getattr(client, "date_of_birth", None)
    age_str = "—"
    if dob_val:
        try:
            today = datetime.now().date()
            age_str = f"{(today - dob_val).days // 365} years"
        except Exception:
            age_str = str(dob_val)

    weight_str = f"{client.weight} kg" if getattr(client, "weight", None) else "—"
    height_str = f"{client.height} cm" if getattr(client, "height", None) else "—"

    profile_items = [
        ("Patient Name", patient_name),
        ("Email / ID", f"{client.email} (ID: {client.id})"),
        ("Demographics", f"Age: {age_str} | Gender: {getattr(client, 'gender', '—') or '—'} | Ht: {height_str} | Wt: {weight_str}"),
        ("Primary Fitness Goal", getattr(client, "fitness_goal", "—") or "General Health & Longevity"),
        ("Nutritional Goal", getattr(client, "nutritional_goal", "—") or "Metabolic Optimization"),
        ("Health Conditions", getattr(client, "health_conditions", "—") or "None reported"),
        ("Dietary Preferences", getattr(client, "dietary_preferences", "—") or "Balanced Whole Foods"),
    ]
    pdf.add_card("Patient Health Profile & Clinical Baseline", profile_items)

    # 3. Healthcare Provider / Physician Review Section
    approved_by = getattr(recommendation, "approved_by", None)
    doctor_notes = getattr(recommendation, "doctor_notes", "") or ""
    doctor_feedback = getattr(recommendation, "doctor_feedback", "") or ""

    if recommendation.status == "APPROVED" or doctor_notes or approved_by:
        provider_name = f"Dr. {approved_by.first_name} {approved_by.last_name}".strip() if approved_by else "Licensed Healthcare Provider"
        approved_time_str = recommendation.approved_at.strftime("%B %d, %Y at %I:%M %p") if recommendation.approved_at else "Verified"
        
        pdf.add_section_header("Clinical Physician Review & Approval", badge_text="APPROVED & PUBLISHED", badge_color=(0.08, 0.45, 0.2))
        
        review_items = [
            ("Reviewing Provider", provider_name),
            ("Approval Timestamp", approved_time_str),
        ]
        if doctor_notes:
            review_items.append(("Physician Notes to Patient", doctor_notes))
        if doctor_feedback:
            review_items.append(("Clinical Feedback & Refinements", doctor_feedback))
            
        pdf.add_card("Clinical Oversight Details", review_items, bg_color=(0.94, 0.98, 0.95))

    # 4. Biomarker Test Context (if linked)
    if biomarker_test:
        results = biomarker_test.results.select_related("biomarker").all()
        if results.exists():
            test_date_str = biomarker_test.recorded_at.strftime("%B %d, %Y") if biomarker_test.recorded_at else "Recent Test"
            pdf.add_section_header("Associated Biomarker Test Session", 
                                   subtitle=f"Biomarker Test #{biomarker_test.id} recorded on {test_date_str}")
            
            table_headers = ["Biomarker", "Measured Value", "Reference Range", "Status"]
            table_rows = []
            for r in results:
                bm = r.biomarker
                ref_range = f"{bm.range_min} - {bm.range_max} {bm.unit}"
                val_str = f"{r.value:.2f} {bm.unit}" if isinstance(r.value, (int, float)) else f"{r.value} {bm.unit}"
                table_rows.append([bm.name, val_str, ref_range, r.status or "NORMAL"])

            pdf.add_table(table_headers, table_rows, col_widths=[180, 110, 142, 100])

    # 5. Precision Dietary Plan
    dietary_data = recommendation.dietary_final or recommendation.dietary_draft or {}
    pdf.add_section_header("Precision Dietary Protocol", icon_text="🥗")

    summary_text = dietary_data.get("summary") or recommendation.text or "A tailored nutritional protocol based on metabolic markers and personal goals."
    pdf.add_paragraph(summary_text, font="Helvetica", size=9.5, color=(0.15, 0.2, 0.25))

    dos = dietary_data.get("dos") or []
    if dos:
        pdf.add_paragraph("Foods & Nutrients to Prioritize (Do's):", font="Helvetica-Bold", size=9.0, color=(0.09, 0.38, 0.22), space_after=3.0)
        for item in dos:
            pdf.add_bullet(str(item), bullet_char="✓")
        pdf.y -= 4

    donts = dietary_data.get("donts") or []
    if donts:
        pdf.add_paragraph("Foods & Ingredients to Avoid / Limit (Don'ts):", font="Helvetica-Bold", size=9.0, color=(0.75, 0.25, 0.15), space_after=3.0)
        for item in donts:
            pdf.add_bullet(str(item), bullet_char="✕")
        pdf.y -= 4

    sample_meals = dietary_data.get("sample_meal_plan") or []
    if sample_meals and isinstance(sample_meals, list):
        meal_headers = ["Meal / Window", "Suggested Menu & Micronutrient Focus"]
        meal_rows = []
        for m in sample_meals:
            if isinstance(m, dict):
                meal_name = m.get("meal", "Meal")
                suggestion = m.get("suggestion", "")
                meal_rows.append([meal_name, suggestion])
        if meal_rows:
            pdf.add_paragraph("Sample Daily Meal Protocol:", font="Helvetica-Bold", size=9.0, color=(0.15, 0.35, 0.28), space_after=4.0)
            pdf.add_table(meal_headers, meal_rows, col_widths=[132, 400])

    # 6. Precision Exercise & Physical Training Plan
    exercise_data = recommendation.exercise_final or recommendation.exercise_draft or {}
    pdf.add_section_header("Exercise & Physical Activity Protocol", icon_text="⚡")

    ex_summary = exercise_data.get("summary") or "A tailored physical training protocol designed to improve insulin sensitivity, cardiovascular efficiency, and body composition."
    pdf.add_paragraph(ex_summary, font="Helvetica", size=9.5, color=(0.15, 0.2, 0.25))

    freq = exercise_data.get("frequency")
    if freq:
        pdf.add_paragraph(f"Prescribed Frequency: {freq}", font="Helvetica-Bold", size=9.0, color=(0.12, 0.35, 0.25), space_after=6.0)

    activities = exercise_data.get("activities") or []
    if activities:
        pdf.add_paragraph("Prescribed Training Modalities:", font="Helvetica-Bold", size=9.0, color=(0.15, 0.25, 0.35), space_after=3.0)
        for act in activities:
            pdf.add_bullet(str(act), bullet_char="→")
        pdf.y -= 4

    precautions = exercise_data.get("precautions") or []
    if precautions:
        pdf.add_paragraph("Clinical Precautions & Injury Prevention:", font="Helvetica-Bold", size=9.0, color=(0.65, 0.3, 0.15), space_after=3.0)
        for p in precautions:
            pdf.add_bullet(str(p), bullet_char="!")
        pdf.y -= 4

    # 7. Medical Disclaimer
    pdf.ensure_space(60)
    disclaimer_text = (
        "Medical Disclaimer: This report contains algorithmic recommendations synthesized by Omiver AI and "
        "reviewed by clinical healthcare professionals. These suggestions are intended for educational and precision "
        "wellness optimization only and do not replace formal diagnosis, prescription, or medical emergency care. "
        "Always consult your primary care physician before beginning new supplementation or rigorous exercise regimens."
    )
    pdf.draw_rect(pdf.MARGIN_LEFT, pdf.y - 40, pdf.content_width, 40, fill_color=(0.96, 0.97, 0.98), stroke_color=(0.88, 0.90, 0.92), line_width=0.5)
    pdf.draw_text("IMPORTANT MEDICAL NOTICE", pdf.MARGIN_LEFT + 8, pdf.y - 12, font="Helvetica-Bold", size=7.5, color=(0.4, 0.45, 0.5))
    lines = pdf.wrap_text(disclaimer_text, pdf.content_width - 16, font="Helvetica-Oblique", size=6.5)
    curr_ly = pdf.y - 20
    for l in lines:
        pdf.draw_text(l, pdf.MARGIN_LEFT + 8, curr_ly, font="Helvetica-Oblique", size=6.5, color=(0.45, 0.5, 0.55))
        curr_ly -= 8.0

    return pdf.build()


def generate_biomarker_report_pdf(report) -> bytes:
    """
    Converts a BiomarkerReport instance into a clean PDF document.
    """
    client = report.client
    patient_name = f"{getattr(client, 'first_name', '')} {getattr(client, 'last_name', '')}".strip() or f"Client #{client.id}"
    
    title = f"Biomarker Report - {patient_name}"
    pdf = SimplePDFBuilder(title=title)

    # Header
    header_box_h = 75.0
    pdf.draw_rect(pdf.MARGIN_LEFT, pdf.y - header_box_h, pdf.content_width, header_box_h, 
                  fill_color=(0.12, 0.30, 0.45))
    
    pdf.draw_text("OMIVER BIOMARKER REPORT", pdf.MARGIN_LEFT + 16, pdf.y - 24, 
                  font="Helvetica-Bold", size=16, color=(1.0, 1.0, 1.0))
    pdf.draw_text("DELTA ANALYSIS & METABOLOMIC INTERVENTION", pdf.MARGIN_LEFT + 16, pdf.y - 42, 
                  font="Helvetica", size=10, color=(0.88, 0.92, 0.98))
    
    created_str = report.created_at.strftime("%B %d, %Y") if report.created_at else datetime.now().strftime("%B %d, %Y")
    pdf.draw_text(f"Report ID: RPT-{report.primary_id:05d}", pdf.PAGE_WIDTH - pdf.MARGIN_RIGHT - 140, pdf.y - 24, 
                  font="Helvetica-Bold", size=9, color=(1.0, 1.0, 1.0))
    pdf.draw_text(f"Date: {created_str}", pdf.PAGE_WIDTH - pdf.MARGIN_RIGHT - 140, pdf.y - 40, 
                  font="Helvetica", size=8.5, color=(0.88, 0.92, 0.98))

    pdf.y -= (header_box_h + 16)

    # Patient info
    profile_items = [
        ("Patient Name", patient_name),
        ("Email / Client ID", f"{client.email} (ID: {client.id})"),
        ("Linked Biomarker Tests", ", ".join(str(t) for t in (report.test_ids or [])) or "Baseline Session"),
    ]
    pdf.add_card("Report Metadata", profile_items)

    # Parse HTML text content into readable sections
    raw_html = report.report or ""
    # Strip basic HTML tags and preserve structure
    cleaned = re.sub(r"<style[\s\S]*?</style>", "", raw_html)
    cleaned = re.sub(r"<script[\s\S]*?</script>", "", raw_html)
    
    # Extract headers and paragraphs
    sections = re.findall(r"<(h[1-3]|p|li|td)[^>]*>(.*?)</\1>", cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    if sections:
        pdf.add_section_header("Report Analysis & Findings", icon_text="📋")
        for tag, content in sections:
            tag = tag.lower()
            text = re.sub(r"<[^>]+>", "", content).strip()
            text = text.replace("&nbsp;", " ").replace("&Delta;", "Delta").replace("&rarr;", "->").replace("&darr;", "-").replace("&amp;", "&")
            if not text:
                continue
            if tag in ["h1", "h2"]:
                pdf.add_section_header(text)
            elif tag == "h3":
                pdf.add_paragraph(text, font="Helvetica-Bold", size=10, color=(0.1, 0.25, 0.35))
            elif tag == "li":
                pdf.add_bullet(text)
            else:
                pdf.add_paragraph(text, size=9)
    else:
        pdf.add_section_header("Summary Report Content")
        plain_text = re.sub(r"<[^>]+>", " ", raw_html)
        pdf.add_paragraph(plain_text)

    return pdf.build()
