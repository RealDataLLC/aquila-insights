"""
Report assembler for AQUILA Office Quarterly Report.
Renders Jinja2 templates to HTML, then converts to PDF via WeasyPrint.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


def _load_arrow_uris(static_dir):
    """Load arrow PNG files as base64 data URIs for embedding in templates."""
    uris = {}
    for name in ('arrow_up', 'arrow_down'):
        path = os.path.join(static_dir, 'arrows', f'{name}.png')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            uris[name] = f'data:image/png;base64,{b64}'
        else:
            uris[name] = None  # fallback to Unicode in template
    return uris


def _build_jinja_env(templates_dir):
    """Create Jinja2 environment with custom filters."""
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=False,
    )
    return env


def _render_title_page(env, config):
    """Render the cover page."""
    tmpl = env.get_template('page_title.html')
    logo_uri = 'file:///' + config.LOGO_PATH.replace('\\', '/')
    return tmpl.render(
        logo_path=logo_uri,
        quarter_display=config.REPORT_LABEL,
        generated_by=config.GENERATED_BY,
    )


def _render_kpi_header(env, config, data, submarket, anchor_id=None, arrow_uris=None, map_image_uri=None):
    """Render a KPI header page for a submarket."""
    from reports.data_loader import get_kpi_data
    kpi = get_kpi_data(data, submarket)
    if not kpi:
        return None
    tmpl = env.get_template('page_kpi_header.html')

    # Create a simple namespace so Jinja2 can access kpi.field
    class KPI:
        pass
    k = KPI()
    k.net_absorption = kpi.get('net_absorption', 0) or 0
    k.avg_rent = kpi.get('avg_rent', 0) or 0
    k.vacancy_rate = kpi.get('vacancy_rate', 0) or 0
    k.under_construction = kpi.get('under_construction', 0) or 0

    arrow_uris = arrow_uris or {}
    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        submarket_name=submarket.upper(),
        kpi=k,
        anchor_id=anchor_id,
        arrow_up_uri=arrow_uris.get('arrow_up'),
        arrow_down_uri=arrow_uris.get('arrow_down'),
        map_image_uri=map_image_uri,
    )


def _render_performance_page(env, config, data, charts, submarket, table_type,
                              display_type=None, anchor_id=None):
    """Render a performance page (table + 3 charts).
    display_type overrides the section label shown on the page.
    """
    from reports.data_loader import get_performance_data
    df = get_performance_data(data, submarket, table_type)
    if df.empty:
        print(f"  Skipping performance page: {submarket} {table_type} (no data)")
        return None

    key = f"{submarket}_{table_type}"
    chart_paths = charts.get(key, {})
    if not chart_paths:
        print(f"  Skipping performance page: {submarket} {table_type} (no charts)")
        return None

    # Convert chart paths to file:// URIs for WeasyPrint
    chart_uris = {}
    for cname, cpath in chart_paths.items():
        chart_uris[cname] = 'file:///' + os.path.abspath(cpath).replace('\\', '/')

    # Convert rows to list of objects for template
    rows = []
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.quarter = row.get('quarter', '')
        r.net_rentable_area = row.get('net_rentable_area', 0) or 0
        r.vacant_available_sf_direct = row.get('vacant_available_sf_direct', 0) or 0
        r.vacant_available_sf_sublet = row.get('vacant_available_sf_sublet', 0) or 0
        r.total_net_absorption = row.get('total_net_absorption', 0) or 0
        r.total_vacancy_rate = row.get('total_vacancy_rate', 0) or 0
        r.full_service_rent = row.get('full_service_rent', 0) or 0
        rows.append(r)

    section_labels = {
        'competitive set': 'Competitive Set',
        'micromarket': 'Micromarket',
        'overall': 'Overall Performance',
    }

    section_label = display_type if display_type else section_labels.get(table_type, table_type.title())

    tmpl = env.get_template('page_performance.html')
    return tmpl.render(
        submarket_name=submarket,
        section_type=section_label,
        rows=rows,
        charts=chart_uris,
        note=None,
        anchor_id=anchor_id,
    )


def _render_major_leases(env, config, data):
    """Render the major leases table page."""
    leases = data.get('leases')
    if leases is None or leases.empty:
        return None

    tmpl = env.get_template('page_major_leases.html')
    rows = []
    for _, row in leases.iterrows():
        class Row:
            pass
        r = Row()
        r.tenant = row.get('Tenant', '')
        r.property_name = row.get('Property Name', '')
        r.submarket = row.get('Submarket', '')
        r.sf_leased = pd.to_numeric(
            str(row.get('SF Leased', 0)).replace(',', ''), errors='coerce') or 0
        r.deal_type = row.get('Deal Type', '')
        rows.append(r)

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        rows=rows,
    )


def _render_major_sales(env, config, data):
    """Render the major sales card grid page."""
    sales = data.get('sales')
    if sales is None or sales.empty:
        return None

    tmpl = env.get_template('page_major_sales.html')
    rows = []
    for _, row in sales.iterrows():
        class Row:
            pass
        r = Row()
        r.property_name = row.get('Property Name', '')
        r.submarket = row.get('Submarket Name', '')
        r.property_type = row.get('Property Type', '')
        r.size = pd.to_numeric(
            str(row.get('Size', 0)).replace(',', ''), errors='coerce') or 0
        r.buyer = row.get('Buyer (True) Company', '')
        r.seller = row.get('Seller (True) Company', '')
        r.asking_price = pd.to_numeric(row.get('Asking Price', 0), errors='coerce') or 0
        rows.append(r)

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        rows=rows,
    )


def _render_large_availability(env, config, data, submarket, rows_per_page=35):
    """Render large availability page(s) for a submarket.
    Returns a list of HTML strings (one per page) with pagination labels.
    """
    avail_data = data.get('office_avail', {})
    if submarket not in avail_data or avail_data[submarket].empty:
        return []

    df = avail_data[submarket].copy()
    tmpl = env.get_template('page_large_availability.html')

    all_rows = []
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.property_name = row.get('property_name', row.get('Property Name', ''))
        r.direct_vacant = pd.to_numeric(
            str(row.get('Direct Vacant Space', row.get('Total Vacant Avail Relet Space (SF)', 0)))
            .replace(',', ''), errors='coerce') or 0
        r.sublet_vacant = pd.to_numeric(
            str(row.get('Sublet Vacant Space', row.get('Total Vacant Avail Sublet Space (SF)', 0)))
            .replace(',', ''), errors='coerce') or 0
        r.max_contiguous = pd.to_numeric(
            str(row.get('Max Contiguous SF', row.get('Max Building Contiguous Space', 0)))
            .replace(',', ''), errors='coerce') or 0
        all_rows.append(r)

    total_pages = max(1, (len(all_rows) + rows_per_page - 1) // rows_per_page)

    pages = []
    for i in range(0, len(all_rows), rows_per_page):
        chunk = all_rows[i:i + rows_per_page]
        page_idx = i // rows_per_page + 1
        page_label = f"(Page {page_idx} of {total_pages})" if total_pages > 1 else ""
        pages.append(tmpl.render(
            submarket_name=submarket,
            rows=chunk,
            page_label=page_label,
        ))
    return pages


def _render_building_list(env, config, data, submarket, rows_per_page=35):
    """Render building list page(s) for a submarket/micromarket.
    Returns a list of HTML strings (one per page) with pagination labels.
    """
    bl_data = data.get('building_list', {})
    if submarket not in bl_data or bl_data[submarket].empty:
        return []

    df = bl_data[submarket].copy()
    tmpl = env.get_template('page_building_list.html')

    all_rows = []
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.building_name = row.get('Building Name(s)', row.get('Building Name', ''))
        r.nra = pd.to_numeric(
            str(row.get('Net Rentable Area', 0)).replace(',', ''), errors='coerce') or 0
        r.direct_vacant = pd.to_numeric(
            str(row.get('Direct Vacant SF', 0)).replace(',', ''), errors='coerce') or 0
        r.sublease_vacant = pd.to_numeric(
            str(row.get('Sublease Vacant SF', 0)).replace(',', ''), errors='coerce') or 0
        all_rows.append(r)

    # Compute totals across ALL rows
    class Totals:
        pass
    t = Totals()
    t.nra = sum(r.nra for r in all_rows)
    t.direct_vacant = sum(r.direct_vacant for r in all_rows)
    t.sublease_vacant = sum(r.sublease_vacant for r in all_rows)

    # Chunk into pages; show totals only on the last page
    total_pages = (len(all_rows) + rows_per_page - 1) // rows_per_page
    pages = []
    for i in range(0, len(all_rows), rows_per_page):
        chunk = all_rows[i:i + rows_per_page]
        page_idx = i // rows_per_page + 1
        page_label = f"(Page {page_idx} of {total_pages})" if total_pages > 1 else ""
        is_last_page = (page_idx == total_pages)
        show_totals = t if is_last_page else None
        pages.append(tmpl.render(
            submarket_name=submarket,
            rows=chunk,
            page_label=page_label,
            totals=show_totals,
        ))
    return pages


def _render_toc(env, config, page_map, city_photo_path=None):
    """
    Render the Table of Contents page.
    page_map is a dict of anchor_id -> page_number (1-based, starting from 1
    for the first content page after title+TOC).
    """
    tmpl = env.get_template('page_toc.html')

    def _entry(anchor, label):
        pg = page_map.get(anchor)
        if pg is None:
            return None
        return {'anchor': anchor, 'label': label, 'page_num': pg}

    # Left column: Citywide update + major transactions + pipeline
    left_entries = []
    for anchor, label in [
        ('citywide-performance',  'Overall Performance'),
        ('major-leases',          'Major Leases & Sales'),
        ('development-pipeline',  'Development Pipeline'),
    ]:
        e = _entry(anchor, label)
        if e:
            left_entries.append(e)

    # Submarket section entries
    submarket_entries = []
    for anchor, label in [
        ('cbd-kpi',   'CBD Submarket'),
        ('nw-kpi',    'Northwest Submarket'),
        ('sw-kpi',    'Southwest Submarket'),
        ('east-kpi',  'East Submarket'),
    ]:
        e = _entry(anchor, label)
        if e:
            submarket_entries.append(e)

    # Appendix entries
    appendix_entries = []
    for anchor, label in [
        ('micromarket-performance',  'Competitive Set Micromarket Performance & Building Lists'),
        ('long-term-performance',    'Long-Term Performance'),
        ('overall-performance',      'Overall Submarket Performance'),
        ('sublease-report',          'Sublease Report & Direct/Sublease Availability'),
    ]:
        e = _entry(anchor, label)
        if e:
            appendix_entries.append(e)

    photo_uri = None
    if city_photo_path and os.path.exists(city_photo_path):
        photo_uri = 'file:///' + city_photo_path.replace('\\', '/')

    return tmpl.render(
        left_entries=left_entries,
        submarket_entries=submarket_entries,
        appendix_entries=appendix_entries,
        city_photo_path=photo_uri,
    )


def _render_quarterly_changes(env, config, data):
    """Render the Quarterly Changes page from CSV data."""
    raw = data.get('quarterly_changes', [])
    if not raw:
        return None

    tmpl = env.get_template('page_quarterly_changes.html')

    sections = []
    for item in raw:
        df = item['df']
        # Identify columns that should NOT get comma formatting (IDs, codes, etc.)
        no_comma_cols = {
            i for i, col in enumerate(df.columns)
            if re.search(r'\bid\b', str(col), re.IGNORECASE)
        }
        rows = []
        for _, row in df.iterrows():
            cells = []
            for col_idx, val in enumerate(row):
                if pd.isna(val):
                    cells.append('—')
                elif col_idx in no_comma_cols:
                    # ID columns: render as plain string, no comma formatting
                    try:
                        fval = float(val)
                        if fval == int(fval):
                            cells.append(str(int(fval)))
                        else:
                            cells.append(str(val))
                    except (ValueError, TypeError):
                        cells.append(str(val))
                else:
                    # Format plain integers with commas, leave strings/floats as-is
                    try:
                        fval = float(val)
                        if fval == int(fval) and abs(fval) < 1e12:
                            cells.append(f"{int(fval):,}")
                        else:
                            cells.append(str(val))
                    except (ValueError, TypeError):
                        cells.append(str(val))
            rows.append(cells)

        sections.append({
            'title': item['title'],
            'columns': item['columns'],
            'rows': rows,
            'empty': item['empty'],
        })

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        sections=sections,
    )


def _render_pipeline(env, config, data):
    """
    Render the development pipeline as two separate pages.
    Returns (uc_html, proposed_html) tuple so each gets its own
    page-counter increment for accurate TOC page numbers.
    """
    pipeline = data.get('pipeline', {})
    if not pipeline:
        return None, None

    # ── Under Construction ────────────────────────────────────────
    # Parse the 'Under Construction' sheet: rows are either group headers
    # (year like 2025/2026, quarter like 1Q/4Q) or data rows.
    uc_groups = []  # list of {year, quarter, rows:[{name, size, pct, submarket}]}
    uc_df = pipeline.get('Under Construction', pd.DataFrame())
    if not uc_df.empty:
        current_year = None
        current_quarter = None
        current_rows = []

        def _flush(year, quarter, rows):
            if rows:
                uc_groups.append({'year': str(year), 'quarter': str(quarter), 'rows': rows})

        for _, row in uc_df.iterrows():
            first = row.iloc[0]
            second = row.iloc[1] if len(row) > 1 else None

            # Skip completely empty rows
            if pd.isna(first):
                continue

            first_str = str(first).strip()

            # Year header (4-digit number)
            if first_str.isdigit() and len(first_str) == 4:
                _flush(current_year, current_quarter, current_rows)
                current_year = first_str
                current_quarter = None
                current_rows = []

            # Quarter header (e.g. "4Q", "1Q", "2Q", "3Q")
            elif first_str[:1].isdigit() and first_str.endswith('Q') or \
                 first_str.endswith('Q') and len(first_str) <= 3:
                _flush(current_year, current_quarter, current_rows)
                current_quarter = first_str
                current_rows = []

            # Data row: name + size (numeric in col 2)
            elif not pd.isna(second) and str(second).replace('.', '', 1).isdigit():
                size_val = pd.to_numeric(second, errors='coerce')
                pct_raw = row.iloc[2] if len(row) > 2 else None
                pct_val = pd.to_numeric(pct_raw, errors='coerce')
                submarket = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else '—'
                current_rows.append({
                    'name': first_str,
                    'size': f"{int(size_val):,}" if not pd.isna(size_val) else '—',
                    'pct': f"{int(pct_val * 100)}%" if not pd.isna(pct_val) else '0%',
                    'submarket': submarket,
                })

        _flush(current_year, current_quarter, current_rows)

    # ── Planned / Proposed ────────────────────────────────────────
    proposed_rows = []
    prop_df = pipeline.get('Proposed', pd.DataFrame())
    if not prop_df.empty:
        # Row 0 is a header row embedded in data; skip it (contains 'Future Developments')
        for _, row in prop_df.iterrows():
            name_val = row.iloc[0]
            size_val = row.iloc[1] if len(row) > 1 else None
            sub_val  = row.iloc[2] if len(row) > 2 else None

            if pd.isna(name_val):
                continue
            name_str = str(name_val).strip()
            # Skip the embedded header row
            if name_str.lower() in ('future developments', 'proposed/planned'):
                continue
            size_num = pd.to_numeric(size_val, errors='coerce')
            proposed_rows.append({
                'name': name_str,
                'size': f"{int(size_num):,}" if not pd.isna(size_num) else '—',
                'submarket': str(sub_val).strip() if not pd.isna(sub_val) else '—',
            })

    if not uc_groups and not proposed_rows:
        return None, None

    tmpl_uc = env.get_template('page_pipeline_uc.html')
    tmpl_proposed = env.get_template('page_pipeline_proposed.html')

    uc_html = tmpl_uc.render(
        quarter_label=config.REPORT_LABEL,
        uc_groups=uc_groups,
    ) if uc_groups else None

    proposed_html = tmpl_proposed.render(
        quarter_label=config.REPORT_LABEL,
        proposed_rows=proposed_rows,
    ) if proposed_rows else None

    return uc_html, proposed_html


def _render_long_term_submarkets(env, config, charts, anchor_id=None):
    """
    Render Page 1 of long-term performance: Of Submarkets.
    6 charts in a 2x3 grid: Citywide/CBD/NW/SW vacancy + asking rates + absorption.
    """
    lt = charts.get('long_term', {})
    required = [
        'lt_vacancy_citywide', 'lt_vacancy_cbd',
        'lt_vacancy_northwest', 'lt_vacancy_southwest',
        'lt_asking_rates', 'lt_absorption',
    ]
    missing = [k for k in required if k not in lt]
    if missing:
        print(f"  Skipping long-term submarkets page (missing charts: {missing})")
        return None

    tmpl = env.get_template('page_long_term_submarkets.html')
    chart_uris = {
        k: 'file:///' + os.path.abspath(lt[k]).replace('\\', '/')
        for k in required
    }
    return tmpl.render(charts=chart_uris, anchor_id=anchor_id)


def _render_long_term_cbd_suburban(env, config, charts, anchor_id=None):
    """
    Render Page 2 of long-term performance: CBD vs Suburban.
    4 charts in a 2x2 grid: asking rates, vacancy, direct/sublease, under construction.
    """
    lt = charts.get('long_term', {})
    required = [
        'lt_cbd_suburban_asking', 'lt_cbd_suburban_vacancy',
        'lt_cbd_suburban_direct_sublease', 'lt_cbd_suburban_under_construction',
    ]
    missing = [k for k in required if k not in lt]
    if missing:
        print(f"  Skipping long-term CBD vs Suburban page (missing charts: {missing})")
        return None

    tmpl = env.get_template('page_long_term_cbd_suburban.html')
    chart_uris = {
        k: 'file:///' + os.path.abspath(lt[k]).replace('\\', '/')
        for k in required
    }
    return tmpl.render(charts=chart_uris, anchor_id=anchor_id)


def _render_sublease_report(env, config, data, rows_per_page=30):
    """Render a sublease report page. Paginates if needed."""
    avail_data = data.get('office_avail', {})
    if 'Subleases' not in avail_data or avail_data['Subleases'].empty:
        return []

    df = avail_data['Subleases'].copy()
    tmpl = env.get_template('page_sublease_report.html')

    # Build all rows
    all_rows = []
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.property_name = row.get('property_name', row.get('Property Name', ''))
        r.tenants = row.get('Tenants', '')
        r.sublease_sf = pd.to_numeric(
            str(row.get('Sublease Available', row.get('vacant_available_sf_direct', 0)))
            .replace(',', ''), errors='coerce') or 0
        r.max_contiguous = pd.to_numeric(
            str(row.get('Max Building Contiguous Space', 0)).replace(',', ''), errors='coerce') or 0
        r.months_on_market = pd.to_numeric(row.get('Months on Market', 0), errors='coerce') or 0
        r.submarket = row.get('submarket_name', row.get('Submarket Name', ''))
        all_rows.append(r)

    # Sort by sublease SF descending (largest first)
    all_rows.sort(key=lambda r: r.sublease_sf, reverse=True)

    # Paginate — first page gets anchor_id, subsequent pages do not
    pages = []
    for i in range(0, len(all_rows), rows_per_page):
        chunk = all_rows[i:i + rows_per_page]
        page_idx = i // rows_per_page + 1
        total_pages = (len(all_rows) + rows_per_page - 1) // rows_per_page
        subtitle = "ALL SUBMARKETS"
        if total_pages > 1:
            subtitle += f" (Page {page_idx} of {total_pages})"
        anchor = 'sublease-report' if page_idx == 1 else None
        pages.append(tmpl.render(
            subtitle=subtitle,
            rows=chunk,
            anchor_id=anchor,
        ))
    return pages


def build_page_sequence(env, config, data, charts, maps=None):
    """
    Build the ordered list of rendered page HTML strings.
    Section order matches the InDesign quarterly report PDF:
      1.  Title page
      1b. Table of Contents (with hyperlinks)
      1c. Quarterly Changes (NRA, Status, Vacancy)
      2.  Citywide KPI + competitive set
      3.  Major Leases
      4.  Major Sales
      4b. Development Pipeline
      5.  Submarket sections: KPI → comp set → large availability (CBD, NW, SW, E)
      6.  Micromarket performance pages
      7.  Overall performance pages
      8.  Sublease report
      9.  Building lists (all regions)

    The TOC is built after all other pages are rendered so we can record
    accurate page numbers (position in the page list + 3 for title/TOC/QC offset).
    """
    # ── Load arrow PNG assets ──────────────────────────────────────
    arrow_uris = _load_arrow_uris(config.STATIC_DIR)

    # ── Load map image data URIs ────────────────────────────────
    map_uris = {}
    if maps:
        for sub_name, png_path in maps.items():
            if os.path.exists(png_path):
                import base64 as _b64
                with open(png_path, 'rb') as f:
                    b64 = _b64.b64encode(f.read()).decode()
                map_uris[sub_name] = f'data:image/png;base64,{b64}'

    # ── Helper to track anchor → page number ─────────────────────
    # Page numbering: title=1, TOC=2, then content starts at 3.
    # We offset content pages by 3 (title + TOC + 1 for 1-based).
    content_pages = []   # list of (html_string, anchor_id_or_None)
    page_map = {}        # anchor_id -> display page number

    pdf_page_counter = [0]  # mutable counter for physical PDF pages

    def _add(html, anchor=None, pdf_pages=1):
        """Add a rendered HTML string to content_pages.
        pdf_pages: number of physical PDF pages this HTML string produces
                   (usually 1, but 2 for pipeline which has two page-break divs).
        """
        if html is None:
            return
        # Physical page number = title(1) + TOC(2) + accumulated pages so far + 1
        page_num = 3 + pdf_page_counter[0]
        content_pages.append(html)
        if anchor:
            page_map[anchor] = page_num
        pdf_page_counter[0] += pdf_pages

    # ── 1c. Quarterly Changes (Internal Use Only) ──────────────────
    # QC pages are excluded from page count and TOC.
    qc_page = _render_quarterly_changes(env, config, data)
    if qc_page:
        content_pages.append(qc_page)
        # Do NOT increment pdf_page_counter — QC is excluded from page numbering
        print("  Rendered: Quarterly Changes (Internal Use Only)")

    # ── 2. Citywide ──────────────────────────────────────────────
    kpi_page = _render_kpi_header(env, config, data, 'Citywide',
                                   anchor_id='citywide-kpi', arrow_uris=arrow_uris,
                                   map_image_uri=map_uris.get('Citywide'))
    _add(kpi_page)
    if kpi_page:
        print("  Rendered: Citywide KPI header")

    perf = _render_performance_page(env, config, data, charts, 'Citywide', 'overall',
                                     display_type='Competitive Set',
                                     anchor_id='citywide-performance')
    _add(perf, anchor='citywide-performance')
    if perf:
        print("  Rendered: Citywide competitive set performance")

    # ── 3. Major Leases ──────────────────────────────────────────
    # anchor is hard-coded in template as id="major-leases"
    leases_page = _render_major_leases(env, config, data)
    _add(leases_page, anchor='major-leases')
    if leases_page:
        print("  Rendered: Major Leases")

    # ── 4. Major Sales ───────────────────────────────────────────
    # anchor is hard-coded in template as id="major-sales"
    sales_page = _render_major_sales(env, config, data)
    _add(sales_page, anchor='major-sales')
    if sales_page:
        print("  Rendered: Major Sales")

    # ── 4b. Development Pipeline ─────────────────────────────────
    # Split into two separate _add() calls so each page gets its own
    # accurate page number in the TOC counter.
    # The UC template has id="development-pipeline" for the TOC anchor.
    uc_page, proposed_page = _render_pipeline(env, config, data)
    _add(uc_page, anchor='development-pipeline')
    _add(proposed_page)
    if uc_page or proposed_page:
        print("  Rendered: Development Pipeline (2 pages)")

    # ── 5. Submarket sections (KPI → comp set → large availability) ──
    # Anchor mapping for the four major submarkets
    _submarket_anchors = {
        'CBD':       ('cbd-kpi',  'cbd-perf'),
        'Northwest': ('nw-kpi',   'nw-perf'),
        'Southwest': ('sw-kpi',   'sw-perf'),
        'East':      ('east-kpi', 'east-perf'),
    }
    for submarket in config.SUBMARKETS_WITH_DETAIL:
        kpi_anchor, _perf_anchor = _submarket_anchors.get(submarket, (None, None))
        kpi_page = _render_kpi_header(env, config, data, submarket,
                                       anchor_id=kpi_anchor, arrow_uris=arrow_uris,
                                       map_image_uri=map_uris.get(submarket))
        _add(kpi_page, anchor=kpi_anchor)
        if kpi_page:
            print(f"  Rendered: {submarket} KPI header")

        perf = _render_performance_page(env, config, data, charts, submarket,
                                         'competitive set')
        _add(perf)
        if perf:
            print(f"  Rendered: {submarket} competitive set performance")

        avail_pages = _render_large_availability(env, config, data, submarket)
        for ap in avail_pages:
            _add(ap)
        if avail_pages:
            print(f"  Rendered: {submarket} large availability ({len(avail_pages)} page(s))")

    # ── 6. Micromarket performance pages ─────────────────────────
    first_micro = True
    for micro in config.MICROMARKETS:
        anchor = 'micromarket-performance' if first_micro else None
        perf = _render_performance_page(env, config, data, charts, micro,
                                         'micromarket', anchor_id=anchor)
        _add(perf, anchor=anchor)
        if perf:
            print(f"  Rendered: {micro} micromarket performance")
            first_micro = False

    # ── 6b. Long-term performance pages ──────────────────────────
    lt_sub_page = _render_long_term_submarkets(env, config, charts,
                                                anchor_id='long-term-performance')
    _add(lt_sub_page, anchor='long-term-performance')
    if lt_sub_page:
        print("  Rendered: Long-term performance – Of Submarkets")

    lt_cbd_page = _render_long_term_cbd_suburban(env, config, charts)
    _add(lt_cbd_page)
    if lt_cbd_page:
        print("  Rendered: Long-term performance – CBD vs Suburban")

    # ── 7. Overall performance pages ─────────────────────────────
    first_overall = True
    for submarket in config.SUBMARKETS_OVERALL:
        anchor = 'overall-performance' if first_overall else None
        perf = _render_performance_page(env, config, data, charts, submarket,
                                         'overall', anchor_id=anchor)
        _add(perf, anchor=anchor)
        if perf:
            print(f"  Rendered: {submarket} overall performance")
            first_overall = False

    # ── 8. Sublease report ───────────────────────────────────────
    sublease_pages = _render_sublease_report(env, config, data)
    first_sublease = True
    for sp in sublease_pages:
        anchor = 'sublease-report' if first_sublease else None
        _add(sp, anchor=anchor)
        first_sublease = False
    if sublease_pages:
        print(f"  Rendered: {len(sublease_pages)} sublease report page(s)")

    # ── 9. Building lists (all regions) ──────────────────────────
    building_list_data = data.get('building_list', {})
    for submarket in building_list_data.keys():
        bl_pages = _render_building_list(env, config, data, submarket)
        for bp in bl_pages:
            _add(bp)
        if bl_pages:
            print(f"  Rendered: {submarket} building list ({len(bl_pages)} page(s))")

    # ── Build TOC now that page numbers are known ─────────────────
    # Place an austin_skyline.jpg in reports/static/ to populate the TOC photo.
    city_photo = os.path.join(config.STATIC_DIR, 'austin_skyline.jpg')
    toc_page = _render_toc(env, config, page_map, city_photo_path=city_photo)
    print("  Rendered: Table of Contents")

    # ── Assemble final page list ──────────────────────────────────
    title_page = _render_title_page(env, config)
    print("  Rendered: Title page")

    pages = [title_page, toc_page] + [html for html in content_pages]
    return pages


def render_html(pages, config):
    """Render all pages into a single HTML document using base.html."""
    env = Environment(
        loader=FileSystemLoader(config.TEMPLATES_DIR),
        autoescape=False,
    )
    base_tmpl = env.get_template('base.html')

    css_report_uri = 'file:///' + os.path.join(config.STATIC_DIR, 'report.css').replace('\\', '/')
    css_tables_uri = 'file:///' + os.path.join(config.STATIC_DIR, 'tables.css').replace('\\', '/')

    html = base_tmpl.render(
        title=config.REPORT_TITLE,
        quarter_label=config.REPORT_LABEL,
        css_report=css_report_uri,
        css_tables=css_tables_uri,
        pages=pages,
    )
    return html


def generate_report(data, charts, config, html_only=False, maps=None):
    """
    Main entry point: render templates → HTML → PDF.
    If html_only=True, skip PDF and just save HTML for browser preview.
    """
    print("\n" + "=" * 60)
    print("ASSEMBLING REPORT")
    print("=" * 60)

    env = _build_jinja_env(config.TEMPLATES_DIR)

    # Build page sequence
    pages = build_page_sequence(env, config, data, charts, maps=maps)
    print(f"\n  Total pages rendered: {len(pages)}")

    # Render full HTML
    html_content = render_html(pages, config)

    # Save HTML
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    html_path = config.OUTPUT_PDF.replace('.pdf', '.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  HTML saved: {html_path}")

    if html_only:
        print("  --html-only mode: skipping PDF generation")
        return html_path

    # Convert to PDF
    print("  Converting to PDF...")
    try:
        html_obj = HTML(string=html_content, base_url=config.STATIC_DIR)
        html_obj.write_pdf(config.OUTPUT_PDF)
        print(f"  PDF saved: {config.OUTPUT_PDF}")
    except ImportError as e:
        print("  ERROR: WeasyPrint is not installed. Skipping PDF generation.")
        print(f"  Details: {e}")
        return html_path
    except Exception as e:
        print("  ERROR: An error occurred during PDF generation.")
        print(f"  Details: {e}")
        return html_path

    print("=" * 60)
    print("REPORT GENERATION COMPLETE")
    print("=" * 60)

    return config.OUTPUT_PDF
