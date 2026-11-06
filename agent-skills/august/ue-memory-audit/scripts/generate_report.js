/**
 * generate_report.js
 * Data-driven UE Memory Audit report generator.
 *
 * Usage:
 *   cd <skill>/scripts
 *   npm install docx          # first run only
 *   node generate_report.js <path/to/report_data.json> <path/to/output.docx>
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, Header, Footer, LevelFormat, PageBreak
} = require('./node_modules/docx');
const fs = require('fs');
const path = require('path');

// ─── ARGS ────────────────────────────────────────────────────────────────────
const dataPath = process.argv[2];
const outPath  = process.argv[3];
if (!dataPath || !outPath) {
  console.error('Usage: node generate_report.js <report_data.json> <output.docx>');
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const meta = D.meta || {};

// ─── COLOURS ─────────────────────────────────────────────────────────────────
const BLUE_DARK  = "1F3864";
const BLUE_MED   = "2E75B6";
const BLUE_LIGHT = "D5E8F0";
const RED_BG     = "FFE0E0";
const AMBER_BG   = "FFF3CD";
const GREEN_BG   = "E8F5E9";
const GREY_BG    = "F5F5F5";

const border    = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders   = { top: border, bottom: border, left: border, right: border };
const noBorder  = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: BLUE_DARK })],
    spacing: { before: 360, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE_MED, space: 4 } }
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: BLUE_MED })],
    spacing: { before: 280, after: 120 }
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: "333333" })],
    spacing: { before: 200, after: 80 }
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text: String(text), font: "Arial", size: 20, color: "333333", ...opts })],
    spacing: { before: 60, after: 60 }
  });
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun({ text, font: "Arial", size: 20, color: "333333" })],
    spacing: { before: 40, after: 40 }
  });
}
function spacer() {
  return new Paragraph({ children: [new TextRun("")], spacing: { before: 80, after: 80 } });
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function cell(text, opts = {}) {
  const { fill = "FFFFFF", bold = false, color = "000000", size = 18, align = AlignmentType.LEFT, width } = opts;
  return new TableCell({
    borders,
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text: String(text ?? ""), font: "Arial", size, bold, color })]
    })]
  });
}
function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: BLUE_DARK, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 18, bold: true, color: "FFFFFF" })]
    })]
  });
}

function statTable(stats) {
  const colW = Math.floor(9360 / stats.length);
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: stats.map(() => colW),
    rows: [new TableRow({
      children: stats.map(s => new TableCell({
        borders: {
          top:    { style: BorderStyle.SINGLE, size: 6, color: s.fill || BLUE_MED },
          bottom: noBorder, left: noBorder, right: noBorder
        },
        shading: { fill: s.bg || GREY_BG, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 120, right: 120 },
        children: [
          new Paragraph({ children: [new TextRun({ text: s.value, font: "Arial", size: 36, bold: true, color: s.fill || BLUE_DARK })] }),
          new Paragraph({ children: [new TextRun({ text: s.label, font: "Arial", size: 18, bold: true, color: "444444" })] }),
          new Paragraph({ children: [new TextRun({ text: s.sub || "", font: "Arial", size: 16, color: "888888" })] }),
        ]
      }))
    })]
  });
}

// ─── SECTION BUILDERS ────────────────────────────────────────────────────────

function buildCriticalTable(rows) {
  const cw = [2200, 700, 1100, 1100, 800, 3460];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          headerCell("Texture Name", cw[0]), headerCell("MB", cw[1]),
          headerCell("Dimensions", cw[2]),   headerCell("Format", cw[3]),
          headerCell("Streams?", cw[4]),      headerCell("Asset Path", cw[5]),
        ]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        const isFloat = (r.fmt || "").includes("Float");
        const noStream = r.stream === "NO";
        return new TableRow({ children: [
          cell(r.name,   { fill: zebra,                                                          bold: true, size: 17, width: cw[0] }),
          cell(r.mb,     { fill: zebra,    bold: true, color: noStream ? "CC0000" : "006600",   align: AlignmentType.RIGHT, width: cw[1] }),
          cell(r.dim,    { fill: zebra,    size: 16,   width: cw[2] }),
          cell(r.fmt,    { fill: isFloat   ? AMBER_BG : (noStream ? RED_BG : zebra), size: 16,  width: cw[3] }),
          cell(r.stream, { fill: noStream  ? RED_BG : GREEN_BG, bold: true, color: noStream ? "CC0000" : "006600", align: AlignmentType.CENTER, width: cw[4] }),
          cell(r.path,   { fill: zebra,    size: 15,   color: "555555",                         width: cw[5] }),
        ]});
      })
    ]
  });
}

function buildNeverStreamTable(rows) {
  const cw = [2400, 700, 1200, 1100, 1000, 2960];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          headerCell("Texture Name", cw[0]), headerCell("MB", cw[1]),
          headerCell("Dimensions", cw[2]),   headerCell("Format", cw[3]),
          headerCell("LOD Group", cw[4]),    headerCell("Notes", cw[5]),
        ]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        return new TableRow({ children: [
          cell(r.name,  { fill: zebra,    bold: true, size: 17, width: cw[0] }),
          cell(r.mb,    { fill: zebra,    bold: true, color: "CC5500", align: AlignmentType.RIGHT, width: cw[1] }),
          cell(r.dim,   { fill: zebra,    size: 16,   width: cw[2] }),
          cell(r.fmt,   { fill: zebra,    size: 16,   width: cw[3] }),
          cell(r.group, { fill: zebra,    size: 16,   width: cw[4] }),
          cell(r.note,  { fill: zebra,    size: 15,   color: "555555", width: cw[5] }),
        ]});
      })
    ]
  });
}

function buildUITable(rows) {
  const cw = [2400, 700, 1200, 5060];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          headerCell("Texture Name", cw[0]),       headerCell("MB", cw[1]),
          headerCell("Current Size", cw[2]),        headerCell("Recommended Action", cw[3]),
        ]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        return new TableRow({ children: [
          cell(r.name,   { fill: zebra,    bold: true, size: 17, width: cw[0] }),
          cell(r.mb,     { fill: zebra,    bold: true, color: "CC5500", align: AlignmentType.RIGHT, width: cw[1] }),
          cell(r.dim,    { fill: zebra,    size: 16,   width: cw[2] }),
          cell(r.action, { fill: AMBER_BG, size: 16,   color: "555500", width: cw[3] }),
        ]});
      })
    ]
  });
}

function buildRTASTable(rows) {
  const cw = [2600, 900, 900, 4960];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          headerCell("Asset", cw[0]),       headerCell("Mesh MB", cw[1]),
          headerCell("RTAS MB", cw[2]),     headerCell("Notes & Recommendation", cw[3]),
        ]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        return new TableRow({ children: [
          cell(r.name,    { bold: true, size: 17, fill: zebra, width: cw[0] }),
          cell(r.mesh_mb, { size: 18, align: AlignmentType.RIGHT, fill: zebra, width: cw[1] }),
          cell(r.rtas_mb, { bold: true, color: "CC5500", size: 18, align: AlignmentType.RIGHT, fill: AMBER_BG, width: cw[2] }),
          cell(r.note,    { size: 16, color: "555555", fill: zebra, width: cw[3] }),
        ]});
      })
    ]
  });
}

function buildAdditionalTable(rows) {
  const cw = [3500, 900, 4960];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [headerCell("Subsystem", cw[0]), headerCell("Size", cw[1]), headerCell("Notes", cw[2])]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        return new TableRow({ children: [
          cell(r.name, { bold: true, size: 17, fill: zebra, width: cw[0] }),
          cell(r.size, { bold: true, color: "886600", align: AlignmentType.RIGHT, fill: AMBER_BG, width: cw[1] }),
          cell(r.note, { size: 16, color: "555555", fill: zebra, width: cw[2] }),
        ]});
      })
    ]
  });
}

function buildPriorityTable(rows) {
  const cw = [3000, 900, 1200, 1200, 3060];
  const priFill  = p => p === "P0" ? RED_BG : p === "P1" ? AMBER_BG : p === "P2" ? "FFF8F0" : GREY_BG;
  const priColor = p => p === "P0" ? "CC0000" : p === "P1" ? "886600" : "555555";
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          headerCell("Issue", cw[0]),        headerCell("Est. Savings", cw[1]),
          headerCell("Effort", cw[2]),        headerCell("Priority", cw[3]),
          headerCell("Action", cw[4]),
        ]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        return new TableRow({ children: [
          cell(r.issue,   { bold: true, size: 17, fill: zebra,          width: cw[0] }),
          cell(r.savings, { bold: true, color: "006600", align: AlignmentType.RIGHT, fill: GREEN_BG, size: 17, width: cw[1] }),
          cell(r.effort,  { size: 17, align: AlignmentType.CENTER, fill: zebra, width: cw[2] }),
          cell(r.priority,{ bold: true, color: priColor(r.priority), align: AlignmentType.CENTER, fill: priFill(r.priority), size: 17, width: cw[3] }),
          cell(r.action,  { size: 16, color: "555555", fill: zebra,    width: cw[4] }),
        ]});
      })
    ]
  });
}

function buildVTTable(rows) {
  const cw = [4000, 1500, 3860];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [headerCell("Pool", cw[0]), headerCell("Size", cw[1]), headerCell("Format", cw[2])]
      }),
      ...rows.map((r, i) => {
        const zebra = i % 2 === 0 ? "FFFFFF" : GREY_BG;
        const warn = (r.format || "").includes("⚠");
        return new TableRow({ children: [
          cell(r.pool,   { fill: zebra, bold: true, size: 18, width: cw[0] }),
          cell(r.size,   { fill: zebra, size: 18, align: AlignmentType.RIGHT, width: cw[1] }),
          cell(r.format, { fill: warn ? AMBER_BG : zebra, size: 18, color: warn ? "886600" : "333333", width: cw[2] }),
        ]});
      })
    ]
  });
}

// ─── DOCUMENT ASSEMBLY ───────────────────────────────────────────────────────
const project   = meta.project  || "Unknown Project";
const build     = meta.build    || "MemReport";
const dateStr   = meta.date     || new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
const sourceStr = meta.source   || `${project} MemReport`;

const children = [];

// Title
children.push(
  spacer(),
  new Paragraph({ children: [new TextRun({ text: project, font: "Arial", size: 64, bold: true, color: BLUE_DARK })], spacing: { before: 480, after: 80 } }),
  new Paragraph({ children: [new TextRun({ text: "Memory Audit Report", font: "Arial", size: 40, color: BLUE_MED })], spacing: { before: 0, after: 80 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: BLUE_MED, space: 8 } } }),
  new Paragraph({ children: [new TextRun({ text: `${build} MemReport  |  ${dateStr}`, font: "Arial", size: 22, color: "888888" })], spacing: { before: 120, after: 480 } }),
);

// Executive Summary
children.push(h1("Executive Summary"));
children.push(body("This report identifies the worst memory offenders in the " + project + " build based on the " + build + " memory report. Three categories of texture problems are analysed: textures that are both uncompressed and never-stream (highest priority), textures that are compressed but permanently resident, and oversized UI textures. Non-texture memory consumers (ray tracing, geometry, plugins, shaders) are covered in later sections."));
children.push(spacer());
if (D.summary_stats && D.summary_stats.length) children.push(statTable(D.summary_stats));
children.push(spacer());
if (D.summary_body) children.push(body(D.summary_body));

// Section 1 — Critical
if (D.critical_textures && D.critical_textures.length) {
  children.push(spacer(), h1("Section 1 — Critical Offenders"), h2("Uncompressed + NeverStream (Worst of Both Worlds)"));
  children.push(body("The following textures are doubly problematic: they use uncompressed pixel formats (typically 4–16× larger than their BC-compressed equivalents) and are also set to never stream, meaning they permanently occupy GPU memory regardless of whether they are visible."));
  children.push(spacer(), buildCriticalTable(D.critical_textures), spacer());
  if (D.critical_summary) children.push(body(D.critical_summary, { bold: true }));
}

// Section 2 — NeverStream Compressed
if (D.neverstream_textures && D.neverstream_textures.length) {
  children.push(spacer(), h1("Section 2 — NeverStream Textures (Compressed)"), h2("Large Textures Locked Resident Without Need"));
  children.push(body("These textures use proper BC compression but have NeverStream set to true. They stay fully resident regardless of camera proximity, blocking the streaming system from managing memory. Textures with 0 usage count are especially suspicious — they may not be referenced by anything currently loaded."));
  children.push(spacer(), buildNeverStreamTable(D.neverstream_textures), spacer());
  if (D.neverstream_bullets && D.neverstream_bullets.length) {
    D.neverstream_bullets.forEach(b => children.push(new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun({ text: b, font: "Arial", size: 20, color: "333333" })],
      spacing: { before: 40, after: 40 }
    })));
  }
}

// Section 3 — UI
if (D.ui_textures && D.ui_textures.length) {
  children.push(spacer(), h1("Section 3 — UI Texture Budget"), h2("Always-Resident UI Group"));
  children.push(body("The TEXTUREGROUP_UI group is entirely non-streaming. The only levers for savings are compression and resolution reduction. UI textures misassigned to TEXTUREGROUP_World compound the problem since they also eat into the world texture pool."));
  children.push(spacer(), buildUITable(D.ui_textures), spacer());
  if (D.ui_note) children.push(body(D.ui_note));
}

// Section 4 — Recommendations
if (D.recommendations && D.recommendations.length) {
  children.push(spacer(), h1("Section 4 — Recommendations"));
  D.recommendations.forEach(rec => {
    children.push(h2(rec.title));
    (rec.bullets || []).forEach(b => children.push(bullet(b)));
  });
  // Format Reference Table (always included)
  children.push(h2("Format Reference — Compression Recommendations"), spacer());
  const fmtCw = [2200, 2200, 2200, 2760];
  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: fmtCw,
    rows: [
      new TableRow({ tableHeader: true, children: [
        headerCell("Current Format", fmtCw[0]), headerCell("Use Case", fmtCw[1]),
        headerCell("Recommended Format", fmtCw[2]), headerCell("Approx. Savings", fmtCw[3])
      ]}),
      ...[
        ["PF_B8G8R8A8", "Colour + Alpha (UI, VFX)",         "BC7",                           "~4:1 compression ratio"],
        ["PF_B8G8R8A8", "Colour only (Decals, World)",       "DXT1 / BC7",                    "~8:1 / ~4:1"],
        ["PF_FloatRGBA","Height / Displacement maps",         "BC6H (HDR) or BC4 (single ch)", "~4:1 to ~8:1"],
        ["PF_FloatRGBA","Normal maps",                        "BC5",                            "~4:1"],
        ["PF_FloatRGBA","Starfield / Sky HDR",                "BC6H",                           "~4:1"],
      ].map((r, i) => new TableRow({ children: [
        cell(r[0], { fill: i%2===0?"FFFFFF":GREY_BG, bold: true, size: 18, width: fmtCw[0] }),
        cell(r[1], { fill: i%2===0?"FFFFFF":GREY_BG, size: 18, width: fmtCw[1] }),
        cell(r[2], { fill: GREEN_BG, bold: true, size: 18, color: "006600", width: fmtCw[2] }),
        cell(r[3], { fill: i%2===0?"FFFFFF":GREY_BG, size: 18, color: "555555", width: fmtCw[3] }),
      ]}))
    ]
  }));
  children.push(spacer());
}

// Section 5 — Geometry & Ray Tracing
if (D.geometry_stats || D.rtas_offenders || D.hair_rt) {
  children.push(pageBreak(), h1("Section 5 — Geometry & Ray Tracing"));

  if (D.geometry_stats && D.geometry_stats.length) {
    children.push(h2("Overall Memory Budget (Top-Level Summary)"), spacer(), statTable(D.geometry_stats), spacer());
  }

  if (D.hair_rt && D.hair_rt.length) {
    children.push(h2("Critical — Hair Ray Tracing"));
    if (D.hair_rt_intro) children.push(body(D.hair_rt_intro), spacer());
    const hrCw = [2800, 900, 5660];
    children.push(new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: hrCw,
      rows: [
        new TableRow({ tableHeader: true, children: [headerCell("Asset", hrCw[0]), headerCell("Size", hrCw[1]), headerCell("Recommendation", hrCw[2])] }),
        ...D.hair_rt.map(r => new TableRow({ children: [
          cell(r.name,           { bold: true, size: 17, fill: RED_BG, width: hrCw[0] }),
          cell(r.size,           { bold: true, color: "CC0000", align: AlignmentType.RIGHT, fill: RED_BG, width: hrCw[1] }),
          cell(r.recommendation, { fill: AMBER_BG, size: 16, color: "555500", width: hrCw[2] }),
        ]}))
      ]
    }));
    children.push(spacer());
  }

  if (D.rtas_offenders && D.rtas_offenders.length) {
    children.push(h2("Ray Tracing Acceleration Structures — Top Offenders"));
    if (D.rtas_intro) children.push(body(D.rtas_intro), spacer());
    children.push(buildRTASTable(D.rtas_offenders), spacer());
    if (D.rtas_note) children.push(body(D.rtas_note));
  }
}

// Section 6 — Additional Findings
if (D.additional_sections && D.additional_sections.length) {
  children.push(spacer(), h1("Section 6 — Additional Findings"));
  D.additional_sections.forEach(sec => {
    children.push(h2(sec.title));
    if (sec.intro) children.push(body(sec.intro), spacer());
    if (sec.table && sec.table.length) { children.push(buildAdditionalTable(sec.table), spacer()); }
    if (sec.body) children.push(body(sec.body));
  });
}

// Section 7 — Priority Table
if (D.priority_table && D.priority_table.length) {
  children.push(spacer(), h1("Section 7 — Summary Priority Table"));
  children.push(body("The following table ranks all identified issues by estimated memory impact and implementation effort."), spacer());
  children.push(buildPriorityTable(D.priority_table), spacer());
}

// Appendix — VT Pools
if (D.vt_pools && D.vt_pools.length) {
  children.push(pageBreak(), h1("Appendix — Virtual Texture Physical Pools"));
  if (D.vt_note) children.push(body(D.vt_note), spacer());
  children.push(buildVTTable(D.vt_pools), spacer());
}

children.push(body(`Source: ${sourceStr} via NotebookLM RAG — ${dateStr}.`, { color: "AAAAAA", size: 18 }));

// ─── BUILD DOCUMENT ──────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
    }]
  },
  styles: { default: { document: { run: { font: "Arial", size: 20 } } } },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: `${project} — Memory Audit`, font: "Arial", size: 18, color: "888888" }),
            new TextRun({ text: `\t${dateStr}`,              font: "Arial", size: 18, color: "888888" })
          ],
          tabStops: [{ type: "right", position: 9360 }],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 4 } }
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: `Generated from ${build} MemReport`, font: "Arial", size: 16, color: "AAAAAA" }),
            new TextRun({ text: "\tPage ", font: "Arial", size: 16, color: "AAAAAA" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "AAAAAA" }),
          ],
          tabStops: [{ type: "right", position: 9360 }],
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 4 } }
        })]
      })
    },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`Done. Written to: ${outPath}`);
}).catch(err => { console.error(err); process.exit(1); });
