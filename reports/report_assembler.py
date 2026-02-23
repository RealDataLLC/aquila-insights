"""
Report assembler for AQUILA Office Quarterly Report.
Renders Jinja2 templates to HTML, then converts to PDF via WeasyPrint.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from jinja2 import Environment, FileSystemLoader


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


def _render_kpi_header(env, config, data, submarket):
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

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        submarket_name=submarket.upper(),
        kpi=k,
    )


def _render_performance_page(env, config, data, charts, submarket, table_type,
                              display_type=None):
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


def _render_large_availability(env, config, data, submarket):
    """Render a large availability page for a submarket."""
    avail_data = data.get('office_avail', {})
    if submarket not in avail_data or avail_data[submarket].empty:
        return None

    df = avail_data[submarket].copy()
    tmpl = env.get_template('page_large_availability.html')

    rows = []
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
        rows.append(r)

    return tmpl.render(
        submarket_name=submarket,
        rows=rows,
    )


def _render_building_list(env, config, data, submarket):
    """Render a building list page for a submarket/micromarket."""
    bl_data = data.get('building_list', {})
    if submarket not in bl_data or bl_data[submarket].empty:
        return None

    df = bl_data[submarket].copy()
    tmpl = env.get_template('page_building_list.html')

    rows = []
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
        rows.append(r)

    # Compute totals
    class Totals:
        pass
    t = Totals()
    t.nra = sum(r.nra for r in rows)
    t.direct_vacant = sum(r.direct_vacant for r in rows)
    t.sublease_vacant = sum(r.sublease_vacant for r in rows)

    return tmpl.render(
        submarket_name=submarket,
        rows=rows,
        totals=t,
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
        rows = []
        for _, row in df.iterrows():
            cells = []
            for val in row:
                if pd.isna(val):
                    cells.append('—')
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
    Render the development pipeline page.
    Left column: Under Construction (grouped by year/quarter).
    Right column: Planned/Proposed (two-column grid).
    """
    pipeline = data.get('pipeline', {})
    if not pipeline:
        return None

    tmpl = env.get_template('page_pipeline.html')

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
        return None

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        uc_groups=uc_groups,
        proposed_rows=proposed_rows,
    )


def _render_sublease_report(env, config, data, page_num=1, rows_per_page=30):
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

    # Paginate
    pages = []
    for i in range(0, len(all_rows), rows_per_page):
        chunk = all_rows[i:i + rows_per_page]
        page_idx = i // rows_per_page + 1
        total_pages = (len(all_rows) + rows_per_page - 1) // rows_per_page
        subtitle = f"ALL SUBMARKETS"
        if total_pages > 1:
            subtitle += f" (Page {page_idx} of {total_pages})"
        pages.append(tmpl.render(
            subtitle=subtitle,
            rows=chunk,
        ))
    return pages


def build_page_sequence(env, config, data, charts):
    """
    Build the ordered list of rendered page HTML strings.
    Section order matches the InDesign quarterly report PDF:
      1.  Title page
      1b. Quarterly Changes (NRA, Status, Vacancy)
      2.  Citywide KPI + competitive set
      3.  Major Leases
      4.  Major Sales
      4b. Development Pipeline
      5.  Submarket sections: KPI → comp set → large availability (CBD, NW, SW, E)
      6.  Micromarket performance pages
      7.  Overall performance pages
      8.  Sublease report
      9.  Building lists (all regions)
    """
    pages = []

    # ── 1. Title page ────────────────────────────────────────────
    pages.append(_render_title_page(env, config))
    print("  Rendered: Title page")

    # ── 1b. Quarterly Changes ─────────────────────────────────────
    qc_page = _render_quarterly_changes(env, config, data)
    if qc_page:
        pages.append(qc_page)
        print("  Rendered: Quarterly Changes")

    # ── 2. Citywide ──────────────────────────────────────────────
    kpi_page = _render_kpi_header(env, config, data, 'Citywide')
    if kpi_page:
        pages.append(kpi_page)
        print("  Rendered: Citywide KPI header")

    perf = _render_performance_page(env, config, data, charts, 'Citywide', 'overall',
                                     display_type='Competitive Set')
    if perf:
        pages.append(perf)
        print("  Rendered: Citywide competitive set performance")

    # ── 3. Major Leases ──────────────────────────────────────────
    leases_page = _render_major_leases(env, config, data)
    if leases_page:
        pages.append(leases_page)
        print("  Rendered: Major Leases")

    # ── 4. Major Sales ───────────────────────────────────────────
    sales_page = _render_major_sales(env, config, data)
    if sales_page:
        pages.append(sales_page)
        print("  Rendered: Major Sales")

    # ── 4b. Development Pipeline ─────────────────────────────────
    pipeline_page = _render_pipeline(env, config, data)
    if pipeline_page:
        pages.append(pipeline_page)
        print("  Rendered: Development Pipeline")

    # ── 5. Submarket sections (KPI → comp set → large availability) ──
    for submarket in config.SUBMARKETS_WITH_DETAIL:
        # KPI header
        kpi_page = _render_kpi_header(env, config, data, submarket)
        if kpi_page:
            pages.append(kpi_page)
            print(f"  Rendered: {submarket} KPI header")

        # Competitive set performance
        perf = _render_performance_page(env, config, data, charts, submarket, 'competitive set')
        if perf:
            pages.append(perf)
            print(f"  Rendered: {submarket} competitive set performance")

        # Large availability (immediately after comp set for this submarket)
        avail_page = _render_large_availability(env, config, data, submarket)
        if avail_page:
            pages.append(avail_page)
            print(f"  Rendered: {submarket} large availability")

    # ── 6. Micromarket performance pages ─────────────────────────
    for micro in config.MICROMARKETS:
        perf = _render_performance_page(env, config, data, charts, micro, 'micromarket')
        if perf:
            pages.append(perf)
            print(f"  Rendered: {micro} micromarket performance")

    # ── 7. Overall performance pages ─────────────────────────────
    for submarket in config.SUBMARKETS_OVERALL:
        perf = _render_performance_page(env, config, data, charts, submarket, 'overall')
        if perf:
            pages.append(perf)
            print(f"  Rendered: {submarket} overall performance")

    # ── 8. Sublease report ───────────────────────────────────────
    sublease_pages = _render_sublease_report(env, config, data)
    for sp in sublease_pages:
        pages.append(sp)
    if sublease_pages:
        print(f"  Rendered: {len(sublease_pages)} sublease report page(s)")

    # ── 9. Building lists (all regions) ──────────────────────────
    building_list_data = data.get('building_list', {})
    for submarket in building_list_data.keys():
        bl_page = _render_building_list(env, config, data, submarket)
        if bl_page:
            pages.append(bl_page)
            print(f"  Rendered: {submarket} building list")

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


def generate_report(data, charts, config, html_only=False):
    """
    Main entry point: render templates → HTML → PDF.
    If html_only=True, skip PDF and just save HTML for browser preview.
    """
    print("\n" + "=" * 60)
    print("ASSEMBLING REPORT")
    print("=" * 60)

    env = _build_jinja_env(config.TEMPLATES_DIR)

    # Build page sequence
    pages = build_page_sequence(env, config, data, charts)
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
    from weasyprint import HTML
    html_obj = HTML(string=html_content, base_url=config.STATIC_DIR)
    html_obj.write_pdf(config.OUTPUT_PDF)
    print(f"  PDF saved: {config.OUTPUT_PDF}")

    print("=" * 60)
    print("REPORT GENERATION COMPLETE")
    print("=" * 60)

    return config.OUTPUT_PDF
