"""
Report assembler for AQUILA Industrial Quarterly Report.
Renders Jinja2 templates to HTML, then converts to PDF via WeasyPrint.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
import pandas as pd
from jinja2 import Environment, FileSystemLoader


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
    """Render the industrial cover page."""
    tmpl = env.get_template('page_industrial_title.html')
    logo_uri = 'file:///' + config.LOGO_PATH.replace('\\', '/')
    return tmpl.render(
        logo_path=logo_uri,
        quarter_display=config.REPORT_LABEL,
        generated_by=config.GENERATED_BY,
    )


def _render_industrial_kpi(env, config, data, arrow_uris=None):
    """
    Render the By the Numbers page with Industrial + Flex KPIs side-by-side
    and pipeline totals. Each section has 4 KPIs:
    Net Absorption, Avg Base Rent, Vacancy Rate, Market Size Change.
    """
    from reports.industrial_data_loader import get_kpi_data, get_performance_data
    ind_kpi = get_kpi_data(data, 'Industrial')
    flex_kpi = get_kpi_data(data, 'Flex')

    if not ind_kpi and not flex_kpi:
        return None

    class KPI:
        pass

    def _make_kpi(raw, property_type):
        k = KPI()
        k.net_absorption = raw.get('net_absorption', 0) or 0
        k.vacancy_rate = raw.get('vacancy_rate', 0) or 0
        k.avg_rent = raw.get('avg_rent', 0) or 0
        k.nra = raw.get('nra', 0) or 0
        # Compute NRA change from prior quarter
        df = get_performance_data(data, 'Regional', property_type, n_quarters=2)
        if len(df) >= 2:
            current_nra = df.iloc[-1].get('net_rentable_area', 0) or 0
            prior_nra = df.iloc[-2].get('net_rentable_area', 0) or 0
            k.nra_change = current_nra - prior_nra
        else:
            k.nra_change = 0
        return k

    ind_k = _make_kpi(ind_kpi, 'Industrial') if ind_kpi else _make_kpi({}, 'Industrial')
    flex_k = _make_kpi(flex_kpi, 'Flex') if flex_kpi else _make_kpi({}, 'Flex')

    # Compute pipeline totals from the pipeline data
    pipeline_uc_sf = 0
    pipeline_proposed_sf = 0
    pipeline = data.get('pipeline', {})
    for sheet_name, df in pipeline.items():
        if df.empty:
            continue
        lower = sheet_name.lower()
        for col in df.columns:
            col_lower = str(col).lower()
            if 'size' in col_lower or 'sf' in col_lower:
                vals = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '', regex=False), errors='coerce'
                ).dropna()
                if 'proposed' in lower or 'planned' in lower:
                    pipeline_proposed_sf += vals.sum()
                else:
                    pipeline_uc_sf += vals.sum()
                break

    arrow_uris = arrow_uris or {}
    tmpl = env.get_template('page_industrial_kpi.html')
    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        industrial_kpi=ind_k,
        flex_kpi=flex_k,
        pipeline_uc_sf=pipeline_uc_sf,
        pipeline_proposed_sf=pipeline_proposed_sf,
        anchor_id='by-the-numbers',
        arrow_up_uri=arrow_uris.get('arrow_up'),
        arrow_down_uri=arrow_uris.get('arrow_down'),
    )


def _render_industrial_performance(env, config, data, charts, submarket, property_type,
                                    anchor_id=None):
    """
    Render an industrial performance page (table + 3 charts).
    Uses 'Average Base Rent' (not 'Full Service Rent').
    """
    from reports.industrial_data_loader import get_performance_data
    df = get_performance_data(data, submarket, property_type)
    if df.empty:
        print(f"  Skipping performance page: {submarket} {property_type} (no data)")
        return None

    key = f"{submarket}_{property_type}"
    chart_paths = charts.get(key, {})
    if not chart_paths:
        print(f"  Skipping performance page: {submarket} {property_type} (no charts)")
        return None

    # Convert chart paths to file:// URIs
    chart_uris = {}
    for cname, cpath in chart_paths.items():
        chart_uris[cname] = 'file:///' + os.path.abspath(cpath).replace('\\', '/')

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
        r.average_rental_rate = row.get('average_rental_rate', 0) or 0
        rows.append(r)

    property_type_label = property_type.upper()

    tmpl = env.get_template('page_industrial_performance.html')
    return tmpl.render(
        property_type_label=property_type_label,
        submarket_name=submarket,
        rows=rows,
        charts=chart_uris,
        anchor_id=anchor_id,
    )


def _render_major_leases(env, config, data):
    """Render the industrial major leases table page."""
    leases = data.get('leases')
    if leases is None or leases.empty:
        return None

    tmpl = env.get_template('page_industrial_major_leases.html')
    rows = []
    for _, row in leases.iterrows():
        class Row:
            pass
        r = Row()
        r.tenant = row.get('Tenant', '')
        r.property_name = row.get('Property Name', '')
        r.submarket = row.get('Submarket', row.get('Submarket Name', ''))
        # Use 'Size (SF)' column name (actual column in the Excel file)
        size_raw = row.get('Size (SF)', row.get('SF Leased', row.get('Size', 0)))
        r.sf_leased = pd.to_numeric(
            str(size_raw).replace(',', ''), errors='coerce') or 0
        r.transaction_type = row.get('Transaction Type', '')
        rows.append(r)

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        rows=rows,
    )


def _render_major_sales(env, config, data):
    """Render the industrial major sales card grid page."""
    sales = data.get('sales')
    if sales is None or sales.empty:
        return None

    tmpl = env.get_template('page_industrial_major_sales.html')
    rows = []
    for _, row in sales.iterrows():
        class Row:
            pass
        r = Row()
        r.property_name = row.get('Property Name', '')
        r.submarket = row.get('Submarket Name', row.get('Submarket', ''))
        r.property_type = row.get('Property Type', '')
        size_raw = row.get('Size', 0)
        r.size = pd.to_numeric(
            str(size_raw).replace(',', ''), errors='coerce') or 0
        r.buyer = row.get('Buyer (True) Company', row.get('Buyer', ''))
        r.seller = row.get('Seller (True) Company', row.get('Seller', ''))
        rows.append(r)

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        rows=rows,
    )


def _render_industrial_pipeline(env, config, data):
    """
    Render the development pipeline page for industrial.
    Updated spreadsheet has proper columns: Quarter Delivery, Name, Size (SF), % Leased, Submarket, Property Type.
    """
    pipeline = data.get('pipeline', {})
    if not pipeline:
        return None

    tmpl = env.get_template('page_industrial_pipeline.html')

    uc_groups = []
    total_uc_sf = 0

    uc_df = pd.DataFrame()
    proposed_df = pd.DataFrame()
    for sheet_name, df in pipeline.items():
        lower = sheet_name.lower()
        if 'proposed' in lower or 'planned' in lower:
            proposed_df = df
        else:
            uc_df = df

    if not uc_df.empty:
        col_names = [str(c).lower() for c in uc_df.columns]
        has_named_cols = any('quarter' in c and 'delivery' in c for c in col_names)

        if has_named_cols:
            # New format: proper named columns
            qd_col = next((c for c in uc_df.columns if 'quarter' in str(c).lower() and 'delivery' in str(c).lower()), None)
            name_col = next((c for c in uc_df.columns if str(c).lower() == 'name'), None)
            size_col = next((c for c in uc_df.columns if 'size' in str(c).lower()), None)
            pct_col = next((c for c in uc_df.columns if 'leased' in str(c).lower()), None)
            sub_col = next((c for c in uc_df.columns if 'submarket' in str(c).lower()), None)

            uc_df = uc_df.dropna(how='all')

            current_quarter = None
            current_rows = []

            def _flush_named(quarter, rows):
                if rows:
                    m = re.match(r'(\d{4})\s*Q(\d)', str(quarter))
                    year = m.group(1) if m else ''
                    q_label = f"{m.group(2)}Q" if m else str(quarter)
                    uc_groups.append({'year': year, 'quarter': f"{q_label} {year}", 'rows': rows})

            for _, row in uc_df.iterrows():
                qd_val = row.get(qd_col) if qd_col else None
                name_val = row.get(name_col) if name_col else None

                if pd.isna(name_val) or str(name_val).strip() == '':
                    continue

                qd_str = str(qd_val).strip() if not pd.isna(qd_val) else ''

                if qd_str and qd_str != str(current_quarter):
                    _flush_named(current_quarter, current_rows)
                    current_quarter = qd_str
                    current_rows = []

                size_val = pd.to_numeric(
                    str(row.get(size_col, 0)).replace(',', '') if size_col else '0',
                    errors='coerce')
                pct_val = pd.to_numeric(row.get(pct_col) if pct_col else None, errors='coerce')
                submarket = str(row.get(sub_col, '---')).strip() if sub_col and not pd.isna(row.get(sub_col)) else '---'

                if not pd.isna(size_val):
                    total_uc_sf += size_val
                    if not pd.isna(pct_val):
                        pct_display = f"{int(pct_val * 100)}%" if pct_val <= 1 else f"{int(pct_val)}%"
                    else:
                        pct_display = '0%'

                    current_rows.append({
                        'name': str(name_val).strip(),
                        'size': f"{int(size_val):,}",
                        'pct': pct_display,
                        'submarket': submarket,
                    })

            _flush_named(current_quarter, current_rows)

        else:
            # Old format: positional columns
            current_year = None
            current_quarter = None
            current_rows = []

            def _flush(year, quarter, rows):
                if rows:
                    uc_groups.append({'year': str(year), 'quarter': str(quarter), 'rows': rows})

            for _, row in uc_df.iterrows():
                first = row.iloc[0]
                second = row.iloc[1] if len(row) > 1 else None

                if pd.isna(first):
                    continue

                first_str = str(first).strip()

                if first_str.isdigit() and len(first_str) == 4:
                    _flush(current_year, current_quarter, current_rows)
                    current_year = first_str
                    current_quarter = None
                    current_rows = []
                elif (first_str[:1].isdigit() and first_str.endswith('Q')) or \
                     (first_str.endswith('Q') and len(first_str) <= 3):
                    _flush(current_year, current_quarter, current_rows)
                    current_quarter = first_str
                    current_rows = []
                elif not pd.isna(second):
                    size_val = pd.to_numeric(str(second).replace(',', ''), errors='coerce')
                    pct_raw = row.iloc[2] if len(row) > 2 else None
                    pct_val = pd.to_numeric(pct_raw, errors='coerce')
                    submarket = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else '---'

                    if not pd.isna(size_val):
                        total_uc_sf += size_val
                        current_rows.append({
                            'name': first_str,
                            'size': f"{int(size_val):,}",
                            'pct': f"{int(pct_val * 100)}%" if not pd.isna(pct_val) and pct_val <= 1 else (
                                f"{int(pct_val)}%" if not pd.isna(pct_val) else '0%'),
                            'submarket': submarket,
                        })

            _flush(current_year, current_quarter, current_rows)

    # ── Planned / Proposed ────────────────────────────────────────
    proposed_rows = []
    total_proposed_sf = 0

    if not proposed_df.empty:
        for _, row in proposed_df.iterrows():
            name_val = row.iloc[0]
            size_val = row.iloc[1] if len(row) > 1 else None
            sub_val = row.iloc[2] if len(row) > 2 else None

            if pd.isna(name_val):
                continue
            name_str = str(name_val).strip()
            if name_str.lower() in ('future developments', 'proposed/planned', 'proposed', 'planned',
                                     'total proposed sf'):
                continue

            size_num = pd.to_numeric(
                str(size_val).replace(',', '') if not pd.isna(size_val) else '',
                errors='coerce')
            if not pd.isna(size_num):
                total_proposed_sf += size_num
            proposed_rows.append({
                'name': name_str,
                'size': f"{int(size_num):,}" if not pd.isna(size_num) else '---',
                'submarket': str(sub_val).strip() if not pd.isna(sub_val) else '---',
            })

    if not uc_groups and not proposed_rows:
        return None

    return tmpl.render(
        quarter_label=config.REPORT_LABEL,
        uc_groups=uc_groups,
        proposed_rows=proposed_rows,
        total_uc_sf=total_uc_sf,
        total_proposed_sf=total_proposed_sf,
    )


def _render_large_availability(env, config, data, generation, rows_per_page=35):
    """
    Render large availability page(s) for a generation (first_gen or second_gen).
    Uses columns: property_name, Property Address, Total Available Space (SF), submarket_name.
    Returns a list of HTML strings (one per page). Returns [] when no data.
    """
    large_avail = data.get('large_avail', {})
    df = large_avail.get(generation, pd.DataFrame())
    if df.empty:
        return []

    generation_labels = {
        'first_gen': 'First-Generation',
        'second_gen': 'Second-Generation',
    }

    tmpl = env.get_template('page_industrial_large_avail.html')

    all_rows = []
    total_sf = 0
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.property_name = row.get('property_name', row.get('Property Name', ''))
        r.property_address = row.get('Property Address', row.get('Address', row.get('property_address', '')))
        # Use the actual column name from the Excel file
        avail_raw = row.get('Total Available Space (SF)',
                           row.get('Available SF',
                           row.get('Available (SF)',
                           row.get('available_sf', 0))))
        r.available_sf = pd.to_numeric(
            str(avail_raw).replace(',', ''), errors='coerce') or 0
        # Use the actual column name from the Excel file
        r.submarket = row.get('submarket_name',
                             row.get('Submarket Name',
                             row.get('Submarket',
                             row.get('submarket', ''))))
        all_rows.append(r)
        total_sf += r.available_sf

    anchor_map = {
        'first_gen': 'large-avail-first-gen',
        'second_gen': 'large-avail-second-gen',
    }

    gen_label = generation_labels.get(generation, generation)
    blurb_text = (f"Large availabilities over 100,000 square feet for "
                  f"{gen_label.lower()} industrial properties in the Austin area.")

    total_pages = max(1, (len(all_rows) + rows_per_page - 1) // rows_per_page)
    pages = []
    for i in range(0, len(all_rows), rows_per_page):
        chunk = all_rows[i:i + rows_per_page]
        page_idx = i // rows_per_page + 1
        page_label = f"(Page {page_idx} of {total_pages})" if total_pages > 1 else ""
        is_last = (page_idx == total_pages)
        pages.append(tmpl.render(
            quarter_label=config.REPORT_LABEL,
            generation_label=gen_label,
            rows=chunk,
            page_label=page_label,
            total_sf=total_sf if is_last and total_sf > 0 else None,
            blurb=blurb_text if page_idx == 1 else "",
            anchor_id=anchor_map.get(generation) if page_idx == 1 else None,
        ))
    return pages


def _render_regional_comparison(env, config, data, charts, property_type, metric,
                                 anchor_id=None):
    """
    Render a regional comparison page: cross-submarket table + multi-line chart.
    Only shows last 8 quarters in the table.
    """
    from reports.industrial_data_loader import get_regional_comparison_data
    comparison_data = get_regional_comparison_data(data, property_type, config.SUBMARKETS)

    if not comparison_data:
        return None

    all_quarters = set()
    for sub, df in comparison_data.items():
        all_quarters.update(df['quarter'].tolist())
    all_quarters = sorted(all_quarters, key=lambda q: _parse_quarter_sort_key(q))

    # Take last 8 quarters only
    if len(all_quarters) > 8:
        all_quarters = all_quarters[-8:]

    metric_col_map = {
        'vacancy_rate': 'total_vacancy_rate',
        'avg_rent': 'average_rental_rate',
    }
    metric_col = metric_col_map.get(metric, metric)

    metric_label_map = {
        'vacancy_rate': 'VACANCY RATE',
        'avg_rent': 'AVERAGE BASE RENT',
    }

    table_rows = []
    for q in all_quarters:
        class RowObj:
            pass
        r = RowObj()
        r.quarter = q
        r.values = []
        for sub in config.SUBMARKETS:
            df = comparison_data.get(sub, pd.DataFrame())
            if not df.empty:
                match = df[df['quarter'] == q]
                if not match.empty:
                    val = match.iloc[0].get(metric_col, float('nan'))
                    if pd.notna(val):
                        if metric == 'vacancy_rate':
                            r.values.append(f"{val:.1%}")
                        elif metric == 'avg_rent':
                            r.values.append(f"${val:,.2f}")
                        else:
                            r.values.append(f"{val:,.0f}")
                    else:
                        r.values.append('---')
                else:
                    r.values.append('---')
            else:
                r.values.append('---')
        table_rows.append(r)

    chart_key = f"regional_comparison_{property_type.lower()}_{metric.replace('avg_rent', 'rent').replace('vacancy_rate', 'vacancy')}"
    chart_path = charts.get(chart_key, '')
    chart_uri = ''
    if chart_path:
        chart_uri = 'file:///' + os.path.abspath(chart_path).replace('\\', '/')

    chart_title_map = {
        'vacancy_rate': f'{property_type} Vacancy Rate by Submarket',
        'avg_rent': f'{property_type} Average Base Rent by Submarket',
    }

    tmpl = env.get_template('page_regional_comparison.html')
    return tmpl.render(
        metric_label=metric_label_map.get(metric, metric.upper()),
        submarkets=config.SUBMARKETS,
        table_rows=table_rows,
        chart_title=chart_title_map.get(metric, ''),
        chart_path=chart_uri,
        anchor_id=anchor_id,
    )


def _render_building_list(env, config, data, sheet_name, rows_per_page=35):
    """Render building list page(s) for a sheet (reuses office template).
    Returns a list of HTML strings (one per page) with pagination labels.
    """
    bl_data = data.get('building_list', {})
    if sheet_name not in bl_data or bl_data[sheet_name].empty:
        return []

    df = bl_data[sheet_name].copy()
    tmpl = env.get_template('page_building_list.html')

    all_rows = []
    for _, row in df.iterrows():
        class Row:
            pass
        r = Row()
        r.building_name = row.get('Building Name(s)', row.get('Building Name', ''))
        r.nra = pd.to_numeric(
            str(row.get('Net Rentable Area', row.get('NRA', 0))).replace(',', ''),
            errors='coerce') or 0
        r.direct_vacant = pd.to_numeric(
            str(row.get('Direct Vacant SF', 0)).replace(',', ''),
            errors='coerce') or 0
        r.sublease_vacant = pd.to_numeric(
            str(row.get('Sublease Vacant SF', 0)).replace(',', ''),
            errors='coerce') or 0
        all_rows.append(r)

    # Compute totals across ALL rows
    class Totals:
        pass
    t = Totals()
    t.nra = sum(r.nra for r in all_rows)
    t.direct_vacant = sum(r.direct_vacant for r in all_rows)
    t.sublease_vacant = sum(r.sublease_vacant for r in all_rows)

    display_name = sheet_name.replace('_', ' ')

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
            submarket_name=display_name,
            rows=chunk,
            page_label=page_label,
            totals=show_totals,
        ))
    return pages


def _render_quarterly_changes(env, config, data):
    """Render the Quarterly Changes page from CSV data."""
    raw = data.get('quarterly_changes', [])
    if not raw:
        return None

    tmpl = env.get_template('page_quarterly_changes.html')

    sections = []
    for item in raw:
        df = item['df']
        no_comma_cols = {
            i for i, col in enumerate(df.columns)
            if re.search(r'\bid\b', str(col), re.IGNORECASE)
        }
        rows = []
        for _, row in df.iterrows():
            cells = []
            for col_idx, val in enumerate(row):
                if pd.isna(val):
                    cells.append('---')
                elif col_idx in no_comma_cols:
                    try:
                        fval = float(val)
                        if fval == int(fval):
                            cells.append(str(int(fval)))
                        else:
                            cells.append(str(val))
                    except (ValueError, TypeError):
                        cells.append(str(val))
                else:
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


def _render_toc(env, config, page_map):
    """Render the Table of Contents for the industrial report."""
    tmpl = env.get_template('page_industrial_toc.html')

    def _entry(anchor, label):
        pg = page_map.get(anchor)
        if pg is None:
            return None
        return {'anchor': anchor, 'label': label, 'page_num': pg}

    regional_entries = []
    for anchor, label in [
        ('by-the-numbers',          'Regional Overall Performance'),
        ('major-leases',            'Major Leases & Sales'),
        ('development-pipeline',    'Development Pipeline'),
        ('large-avail-first-gen',   'Large Availabilities'),
    ]:
        e = _entry(anchor, label)
        if e:
            regional_entries.append(e)

    submarket_entries = []
    for submarket in config.SUBMARKETS:
        slug = submarket.lower().replace(' ', '-')
        anchor = f"{slug}-submarket"
        e = _entry(anchor, f"{submarket} Submarket")
        if e:
            submarket_entries.append(e)

    appendix_entries = []
    for anchor, label in [
        ('building-lists',  'Building Lists'),
    ]:
        e = _entry(anchor, label)
        if e:
            appendix_entries.append(e)

    return tmpl.render(
        regional_entries=regional_entries,
        submarket_entries=submarket_entries,
        appendix_entries=appendix_entries,
    )


def _parse_quarter_sort_key(q_str):
    """Convert '2025 Q4' to sortable value."""
    m = re.match(r'(\d{4})\s*Q(\d)', str(q_str))
    if m:
        return int(m.group(1)) + int(m.group(2)) / 10
    return 0


def build_page_sequence(env, config, data, charts):
    """
    Build the ordered list of rendered page HTML strings.
    """
    content_pages = []
    page_map = {}
    pdf_page_counter = [0]

    # ── Load arrow PNG assets ──────────────────────────────────────
    arrow_uris = _load_arrow_uris(config.STATIC_DIR)

    def _add(html, anchor=None, pdf_pages=1):
        if html is None:
            return
        page_num = 3 + pdf_page_counter[0]
        content_pages.append(html)
        if anchor:
            page_map[anchor] = page_num
        pdf_page_counter[0] += pdf_pages

    # By the Numbers
    kpi_page = _render_industrial_kpi(env, config, data, arrow_uris=arrow_uris)
    _add(kpi_page, anchor='by-the-numbers')
    if kpi_page:
        print("  Rendered: By the Numbers")

    # Quarterly Changes (Internal Use Only) — excluded from page count and TOC
    qc_page = _render_quarterly_changes(env, config, data)
    if qc_page:
        content_pages.append(qc_page)
        # Do NOT increment pdf_page_counter — QC is excluded from page numbering
        print("  Rendered: Quarterly Changes (Internal Use Only)")

    # Major Leases
    leases_page = _render_major_leases(env, config, data)
    _add(leases_page, anchor='major-leases')
    if leases_page:
        print("  Rendered: Major Leases")

    # Major Sales
    sales_page = _render_major_sales(env, config, data)
    _add(sales_page, anchor='major-sales')
    if sales_page:
        print("  Rendered: Major Sales")

    # Development Pipeline
    pipeline_page = _render_industrial_pipeline(env, config, data)
    _add(pipeline_page, anchor='development-pipeline', pdf_pages=2)
    if pipeline_page:
        print("  Rendered: Development Pipeline")

    # Large Availabilities
    for gen in ['first_gen', 'second_gen']:
        avail_pages = _render_large_availability(env, config, data, gen)
        anchor = f"large-avail-{gen.replace('_', '-')}"
        for ap in avail_pages:
            _add(ap, anchor=anchor)
            anchor = None  # Only first page gets the anchor
        if avail_pages:
            label = 'First Generation' if gen == 'first_gen' else 'Second Generation'
            print(f"  Rendered: Large Availabilities -- {label} ({len(avail_pages)} page(s))")

    # Regional Overall
    for ptype in config.PROPERTY_TYPES:
        anchor = f"regional-{ptype.lower()}"
        perf = _render_industrial_performance(env, config, data, charts,
                                               'Regional', ptype,
                                               anchor_id=anchor)
        _add(perf, anchor=anchor)
        if perf:
            print(f"  Rendered: Regional Overall -- {ptype}")

    # Regional Comparison
    first_comparison = True
    for ptype in config.PROPERTY_TYPES:
        for metric in ['vacancy_rate', 'avg_rent']:
            anchor = 'regional-comparison' if first_comparison else None
            comp_page = _render_regional_comparison(env, config, data, charts,
                                                     ptype, metric,
                                                     anchor_id=anchor)
            _add(comp_page, anchor=anchor)
            if comp_page:
                label = 'Vacancy Rate' if metric == 'vacancy_rate' else 'Avg Base Rent'
                print(f"  Rendered: Regional Comparison -- {ptype} {label}")
                first_comparison = False

    # Submarket sections
    for submarket in config.SUBMARKETS:
        slug = submarket.lower().replace(' ', '-')
        first_type = True
        for ptype in config.PROPERTY_TYPES:
            anchor = f"{slug}-submarket" if first_type else None
            perf = _render_industrial_performance(env, config, data, charts,
                                                   submarket, ptype,
                                                   anchor_id=anchor)
            _add(perf, anchor=anchor)
            if perf:
                print(f"  Rendered: {submarket} -- {ptype}")
                first_type = False

    # Building Lists
    bl_data = data.get('building_list', {})
    first_bl = True
    for sheet_name in bl_data.keys():
        anchor = 'building-lists' if first_bl else None
        bl_pages = _render_building_list(env, config, data, sheet_name)
        for bp in bl_pages:
            _add(bp, anchor=anchor)
            anchor = None  # Only first page gets the anchor
        if bl_pages:
            print(f"  Rendered: {sheet_name} building list ({len(bl_pages)} page(s))")
            first_bl = False

    # Build TOC
    toc_page = _render_toc(env, config, page_map)
    print("  Rendered: Table of Contents")

    title_page = _render_title_page(env, config)
    print("  Rendered: Title page")

    pages = [title_page, toc_page] + content_pages
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
    """Main entry point: render templates -> HTML -> PDF."""
    print("\n" + "=" * 60)
    print("ASSEMBLING INDUSTRIAL REPORT")
    print("=" * 60)

    env = _build_jinja_env(config.TEMPLATES_DIR)
    pages = build_page_sequence(env, config, data, charts)
    print(f"\n  Total pages rendered: {len(pages)}")

    html_content = render_html(pages, config)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    html_path = config.OUTPUT_PDF.replace('.pdf', '.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  HTML saved: {html_path}")

    if html_only:
        print("  --html-only mode: skipping PDF generation")
        return html_path

    print("  Converting to PDF...")
    from weasyprint import HTML
    html_obj = HTML(string=html_content, base_url=config.STATIC_DIR)
    html_obj.write_pdf(config.OUTPUT_PDF)
    print(f"  PDF saved: {config.OUTPUT_PDF}")

    print("=" * 60)
    print("INDUSTRIAL REPORT GENERATION COMPLETE")
    print("=" * 60)

    return config.OUTPUT_PDF
