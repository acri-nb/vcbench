from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
import ast

emedgene_data = {
    "report_data": {
        "most_likely_variants": [{
            "GnomAD_Max_AF": None,
            "GnomAD_max_AC": None,
            "acmg_classification": None,
            "acmg_tags": None,
            "acmg_tags_checked": None,
            "articles": None,
            "dbSNP_ID": None,
            "diseases": None,
            "evidence_graph": {
                "nodes": None
            },
            "father_zygosity": None,
            "mother_zygosity": None,
            "isoform": None,
            "nucleotide": None,
            "predictions": None,
            "proband_zygosity": None,
            "splice_prediction": None
        }],
        "quality": {
            "test_subject": {
                "dragen_metrics": None,
                "ploidy": {
                    "karyotype": None,
                    "ploidy_ratio": None
                },
                "vcf_quality": {
                    "error_rate": None
                }
            }
        },
        "test": {
            "name": None,
            "notes": None,
            "recommendations": None,
            "references": None
        }
    }
}

styles = getSampleStyleSheet()

def main():
    doc = SimpleDocTemplate("clinical_report.pdf", pagesize=LETTER)
    elements = []
    # Create header with logo
    elements.append(create_header("logo-vitalite2020web.png", "Clinical Report"))
    # Create patient information block
    info_fields = [
        "PATIENT",
        "DOB",
        "SEX",
        "MRN#",
        "SPECIMEN TYPE",
        "SPECIMEN QUALITY",
        "COLLECTED",
        "RECEIVED",
        "LAB NUMBER",
        "REPORT DATE",
        "ORDERING PHYSICIAN"
    ]
    elements.append(create_info_block(info_fields))
    # Read emedgene data
    data = get_emedgene_data("json_output_emedgene.json")
    # Add most likely variants data
    elements.extend(most_likely_variants(data["report_data"]["most_likely_variants"]))
    # Add quality data
    elements.extend(add_quality(data["report_data"]["quality"]["test_subject"]))
    # Add test data
    elements.extend(add_test(data["report_data"]["test"]))
    # Build pdf document
    doc.build(elements)


def create_header(logo_path, title_str):
    # Create logo
    logo = Image(logo_path)
    scale = 0.4
    logo.drawWidth = logo.imageWidth * scale
    logo.drawHeight = logo.imageHeight * scale
    # Create title
    title = Paragraph("Clinical Report", styles["Title"])
    # Create 1 row, 2 column table
    header_table = Table(data=[[logo, title]], colWidths=[70, 460])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), -40),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), -50),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
    ]))
    
    return header_table


def create_info_block(info_fields):
    normal = styles["Normal"]
    data = []
    # Pad the list to ensure it's a multiple of 3
    while len(info_fields) % 3 != 0:
        info_fields.append("")
    #Create data fields
    row = []
    for field in info_fields:
        if field != "":
            field += ":"
        label = Paragraph(f"<b>{field}</b>", normal)
        row.append(label)
        if len(row) == 3:
            data.append(row)
            row = []
    # Create fields table
    fields_table = Table(data, colWidths=[180, 180, 180])
    fields_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10)
    ]))
    
    return fields_table


def get_emedgene_data(filepath):
    with open(filepath) as f:
        next(f) # Skip header
        data = ast.literal_eval(f.read())
        
        return trim_data(data, emedgene_data)
        
      
# Recursively trim emedgene data  
def trim_data(data, req_data):
    if isinstance(req_data, dict):
        result = {}
        for key, sub_req in req_data.items():
            if key in data:
                result[key] = trim_data(data[key], sub_req)
        return result

    elif isinstance(req_data, list):
        # Use [{}] or [None] to indicate structure
        if isinstance(data, list) and req_data:
            return [trim_data(item, req_data[0]) for item in data if isinstance(item, dict)]
        elif isinstance(data, list):
            return data  # Pass through list if no structure is defined
        else:
            return []  # fallback

    elif req_data is None:
        return data  # Keep the actual value

    else:
        return None  # If req_data is invalid type, skip


def most_likely_variants(variants):
    elements = []
    #Section title
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b><u>Most Likely Variants</u></b>", styles["Heading1"]))
    # Iterate through the variants
    for i, var in enumerate(variants):
        # Add the variant identifier, variant # if identifier not found
        gene = var.get("evidence_graph", {}).get("nodes", [{}])[0].get("name", f"Variant {i+1}")
        hgvs = var.get("isoform") or var.get("nucleotide") or "Unknown"
        header = f"{gene} {hgvs}"
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>{header}</b>", styles["Heading2"]))
        # Add evidence graph data
        elements.extend(add_evidence_graph(var.get("evidence_graph", []).get("nodes", [])))
        # Add acmg data
        elements.extend(add_acmg_info(var))
        # Add diseases
        elements.append(KeepTogether(add_diseases(var.get("diseases", []))))
        elements.append(Spacer(1, 10))
        # Add Single valued fields
        rows = []
        fields = [
            ("dbSNP ID", var.get("dbSNP_ID")),
            ("Proband Zygosity", var.get("proband_zygosity")),
            ("Father Zygosity", var.get("father_zygosity")),
            ("Mother Zygosity", var.get("mother_zygosity")),
            ("GnomAD Max AF", var.get("GnomAD_Max_AF")),
            ("GnomAD Max AC", var.get("GnomAD_max_AC")),
            ("Predictions", var.get("predictions")),
            ("Splice Prediction", var.get("splice_prediction")),
        ]
        for label, value in fields:
            val = str(value) if value not in [None, ""] else "<i>None</i>"
            rows.append([Paragraph(f"<b>{label}</b>", styles["Normal"]), Paragraph(val, styles["Normal"])])

        table = Table(rows, colWidths=[180, 340], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
        # Add articles 
        elements.append(add_articles(var))

    return elements


def add_acmg_info(var):
    elements = []
    # Add classificaton
    classification = [[
            Paragraph("<b>ACMG Classification</b>", styles["Normal"]),
            Paragraph(var.get("acmg_classification", ""), styles["Normal"])
    ]]
    classification_table = Table(classification, colWidths=[180, 340], hAlign='LEFT')
    classification_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4)
    ]))
    elements.append(classification_table)
    # Add table of acmg tags
    tags = [["Criterion", "Strength"]]
    for tag in var.get("acmg_tags_checked"):
        tags.append([tag["criterion"].replace("_", " "), tag["strength"].replace("_", " ")])
    tags_table = Table(tags, colWidths=[180, 180], hAlign='LEFT')
    tags_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3)
    ]))
    elements.append(tags_table)
    elements.append(Spacer(1, 12))
    
    return elements


def add_articles(var):
    article_rows = []
    article_heading = Paragraph("<b>Articles</b>", styles["Normal"])
    article_rows.append([article_heading, ""])
    for article in var.get("articles", []):
        title = Paragraph(article.get("title", "Untitled"), styles["Normal"])
        url_text = article.get("url", "")
        url = Paragraph(f"<a href='{url_text}'>{url_text}</a>", styles["Normal"])
        article_rows.append([title, url])
    article_table = Table(article_rows, colWidths=[220, 300], hAlign='LEFT')
    article_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    return article_table


def add_evidence_graph(nodes):
    elements = []
    # Add single valued fields
    rows = []
    fields = [
        ("Transcript", nodes[0].get("transcript")),
        ("Zygosity", nodes[0].get("zygosity")),
        ("Ensembl ID", nodes[1].get("ensembl_id")),
        ("HGNC ID", nodes[1].get("hgnc_id")),
        ("Gene Name", nodes[1].get("name"))
    ]
    for label, value in fields:
            val = str(value) if value not in [None, ""] else "<i>None</i>"
            rows.append([Paragraph(f"<b>{label}</b>", styles["Normal"]), Paragraph(val, styles["Normal"])])
    table = Table(rows, colWidths=[180, 340], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    # Add Patient phenotypes field
    rows = []
    phenotype_heading = Paragraph("<b>Patient Phenotypes</b>", styles["Normal"])
    rows.append([phenotype_heading, ""])
    rows.append(["Name", "Match"])
    for phenotype in nodes[3].get("phenotypes", []):
        rows.append([phenotype.get("name"), phenotype.get("matchType")])
    phenotypes_table = Table(rows, colWidths=[180, 180], hAlign='LEFT')
    phenotypes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('GRID', (0, 1), (-1, -1), 0.25, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3)
    ]))
    elements.append(phenotypes_table)
    elements.append(Spacer(1, 6))
    
    return elements
    
   
def add_diseases(diseases):
    rows = []
    # Add heading and column names
    diseases_heading = Paragraph("<b>Diseases</b>", styles["Normal"])
    rows.append([diseases_heading, "", "", ""])
    rows.append(["Linked Disease", "OMIM ID", "Inheritance", "Description"])
    # Add each disease from data
    for disease in diseases:
        current_row = []
        for field in ["name", "omim_id", "inheritance", "uniprot_desc"]:
            value = disease.get(field)
            text = str(value) if value is not None else "Unknown"
            current_row.append(Paragraph(text, styles["Normal"]))
        rows.append(current_row)
    diseases_table = Table(rows, colWidths=[90, 60, 60, 240], hAlign='LEFT')
    diseases_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('GRID', (0, 1), (-1, -1), 0.25, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3)
    ])) 
    
    return diseases_table
     

def add_quality(test_subject):
    elements = []
    # Add Section title
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b><u>Quality</u></b>", styles["Heading1"]))
    elements.append(Spacer(1, 20))
    # Add single value fields
    rows = [
        [
            Paragraph("<b>Mean Target Coverage</b>", styles["Normal"]),
            Paragraph(str(test_subject.get("dragen_metrics").get("MEAN_TARGET_COVERAGE")), styles["Normal"])
        ],
        [
            Paragraph("<b>Karyotype</b>", styles["Normal"]),
            Paragraph(test_subject.get("ploidy").get("karyotype"), styles["Normal"])
        ],
        [
            Paragraph("<b>Error rate</b>", styles["Normal"]),
            Paragraph(str(test_subject.get("vcf_quality").get("error_rate")), styles["Normal"])
        ]
    ]
    table = Table(rows, colWidths=[180, 340], hAlign='LEFT')
    elements.append(table)
    # Add PCT target bases bar chart
    pct_target_bases = Paragraph("<b>PCT Target Bases</b>", styles["Normal"])
    elements.append(Table([[pct_target_bases]], colWidths=[180, 180], hAlign='LEFT'))
    drawing = Drawing(400, 200)
    chart_data = [[
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_2X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_10X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_20X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_30X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_40X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_50X", 0)),
        float(test_subject.get("dragen_metrics", 0).get("PCT_TARGET_BASES_100X", 0))
    ]]
    chart = VerticalBarChart()
    chart.x, chart.y = 50, 50
    chart.height, chart.width = 140, 300
    chart.data = chart_data
    chart.strokeColor = colors.black
    chart.valueAxis.valueMin, chart.valueAxis.valueMax = 0, 1
    chart.valueAxis.valueStep = 0.1
    chart.categoryAxis.categoryNames = [
        "2X",
        "10X",
        "20X",
        "30X",
        "40X",
        "50X",
        "100X"
    ]
    chart.bars[0].fillColor = colors.darkblue
    drawing.add(chart)
    elements.append(drawing)
    # Add ploidy ratio graph
    title = Paragraph("<b>Ploidy Ratio</b>", styles["Normal"])
    ploidy_ratio_title = Table([[title]], colWidths=[180, 180], hAlign='LEFT')
    category_names = []
    chart_data = []
    for i in range(1, 23):
        category_names.append(f"{i}")
        chart_data.append(test_subject.get("ploidy").get("ploidy_ratio").get(f"chr{i}"))
    chrX = test_subject.get("ploidy").get("ploidy_ratio").get("chrX")
    if chrX != 0:
        category_names.append("X")
        chart_data.append(chrX)
    chrY = test_subject.get("ploidy").get("ploidy_ratio").get("chrY")
    if chrY != 0:
        category_names.append("Y")
        chart_data.append(chrY)
    drawing = Drawing(500, 200)
    chart = VerticalBarChart()
    chart.x, chart.y = 50, 50
    chart.height, chart.width = 140, 400
    chart.data = [chart_data]
    chart.strokeColor = colors.black
    chart.valueAxis.valueMin, chart.valueAxis.valueMax = 0.9, 1.1
    chart.valueAxis.valueStep = 0.02
    chart.valueAxis.labelTextFormat = '%.2f'
    chart.categoryAxis.categoryNames = category_names
    chart.bars[0].fillColor = colors.darkblue
    drawing.add(chart)
    elements.append(KeepTogether([ploidy_ratio_title, drawing]))
    
    return elements


def add_test(test):
    elements = []
    # Add section title
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b><u>Test</u></b>", styles["Heading1"]))
    elements.append(Spacer(1, 20))
    # Add data 
    rows = [
        [
            Paragraph("<b>Name</b>", styles["Normal"]),
            Paragraph(str(test.get("name")), styles["Normal"])
        ],
        [
            Paragraph("<b>Notes</b>", styles["Normal"]),
            Paragraph(str(test.get("notes")), styles["Normal"])
        ],
        [
            Paragraph("<b>Recommendations</b>", styles["Normal"]),
            Paragraph(str(test.get("recommendations")), styles["Normal"])
        ],
        [
            Paragraph("<b>References</b>", styles["Normal"]),
            Paragraph(str(test.get("references")), styles["Normal"])
        ]
    ]
    table = Table(rows, colWidths=[180, 340], hAlign='LEFT')
    elements.append(table)
    
    return elements
    


if __name__ == "__main__":
    main()