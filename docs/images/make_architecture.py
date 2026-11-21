"""Generates docs/images/architecture.svg (LiveAsk architecture on AWS).

Run:  python docs/images/make_architecture.py
Edit the coordinates below and re-run; the SVG is plain and diff-friendly.
"""

from pathlib import Path

W, H = 1440, 900
INK = "#232F3E"
MUTED = "#5F6B7A"

# AWS architecture icon category colors
NET = "#8C4FFF"
SEC = "#DD344C"
CMP = "#ED7100"
DB = "#C925D1"
FIN = "#7AA116"
K8S = "#326CE5"

REQ = "#0972D3"   # client traffic
DATA = "#E07941"  # database traffic and NOTIFY
OPS = "#3F8624"   # delivery

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def group(x, y, w, h, label, stroke, fill="none", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{d}/>')
    add(f'<rect x="{x}" y="{y}" width="{len(label) * 7.4 + 22}" height="24" rx="6" fill="{stroke}"/>')
    add(f'<text x="{x + 11}" y="{y + 16.5}" class="glabel">{esc(label)}</text>')


def tile(cx, cy, color, glyph, label, sub=None, size=52, round_=False):
    h = size / 2
    if round_:
        add(f'<circle cx="{cx}" cy="{cy}" r="{h}" fill="{color}"/>')
    else:
        add(f'<rect x="{cx - h}" y="{cy - h}" width="{size}" height="{size}" rx="10" fill="{color}"/>')
    fs = 15 if len(glyph) <= 4 else 12
    add(f'<text x="{cx}" y="{cy + fs * 0.35}" class="glyph" font-size="{fs}">{esc(glyph)}</text>')
    add(f'<text x="{cx}" y="{cy + h + 17}" class="tlabel">{esc(label)}</text>')
    if sub:
        add(f'<text x="{cx}" y="{cy + h + 32}" class="tsub">{esc(sub)}</text>')


def pill(x, y, w, label, color):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="14" fill="#fff" stroke="{color}" stroke-width="1.4"/>')
    add(f'<circle cx="{x + 16}" cy="{y + 14}" r="5" fill="{color}"/>')
    add(f'<text x="{x + 28}" y="{y + 18.5}" class="pill">{esc(label)}</text>')


def path(d, color=INK, dashed=False, arrow=True, width=1.8):
    da = ' stroke-dasharray="6 5"' if dashed else ""
    m = f' marker-end="url(#a-{color.strip("#")})"' if arrow else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da}{m}/>')


def tag(x, y, text, color=INK):
    w = len(text) * 6.3 + 14
    add(f'<rect x="{x - w / 2}" y="{y - 11}" width="{w}" height="20" rx="10" fill="#fff" stroke="{color}" stroke-width="1"/>')
    add(f'<text x="{x}" y="{y + 3.5}" class="tag" fill="{color}">{esc(text)}</text>')


def step(x, y, n, color):
    add(f'<circle cx="{x}" cy="{y}" r="11" fill="{color}"/>')
    add(f'<text x="{x}" y="{y + 4.5}" class="step">{n}</text>')


# ---------------------------------------------------------------- header
add(f'<rect width="{W}" height="{H}" rx="18" fill="#FFFFFF"/>')
add('<text x="40" y="48" class="title">LiveAsk</text>')
add('<text x="40" y="72" class="subtitle">Real-time Q&amp;A and polls for presentations · Amazon EKS · ap-southeast-1</text>')

# ---------------------------------------------------------------- groups
group(200, 92, 1210, 738, "AWS Cloud", INK)
group(220, 132, 1170, 678, "Region ap-southeast-1", "#00A4A6", dash="7 5")
group(240, 172, 900, 618, "VPC 10.20.0.0/16 · 2 AZs", NET, fill="#FBF9FF")
group(258, 212, 174, 558, "Public subnets", FIN, fill="#F3F8EA")
group(450, 212, 480, 558, "Private subnets", "#147EBA", fill="#EEF6FC")
group(470, 252, 440, 498, "Amazon EKS cluster · Spot nodes in 2 AZs", CMP, fill="#FFFFFF")
group(488, 292, 404, 290, "namespace: liveask", K8S, fill="#F5F8FE", dash="5 4")
group(950, 212, 172, 330, "Database subnets", DB, fill="#FBF1FC")

# ---------------------------------------------------------------- arrows (under tiles)
# clients -> ALB
path("M126,250 H230 V380 H316", REQ)
path("M126,380 H316", REQ)
path("M126,510 H230 V380", REQ, arrow=False)
# ALB -> pods (target-type ip)
path("M372,380 H520 V340 H532", REQ)
path("M520,380 V460 H532", REQ)
# pods / cronjob -> RDS
path("M588,340 H640 V395", DATA, arrow=False)
path("M588,450 H640 V395", DATA, arrow=False)
path("M740,484 V395", DATA, arrow=False)
path("M640,395 H1006", DATA)
# NOTIFY back to every pod
path("M1022,352 C1018,268 700,262 590,318", DATA, dashed=True)
path("M1010,408 C900,470 690,474 590,474", DATA, dashed=True)
# delivery
path("M126,700 H170 V796 H1250 V752", OPS)
path("M690,796 V754", OPS, dashed=True)
path("M1224,690 H914", CMP, dashed=True)

# ---------------------------------------------------------------- outside
tile(100, 250, "#545B64", "aud", "Audience", "phones · QR code", round_=True)
tile(100, 380, "#545B64", "host", "Presenter", "secret host link", round_=True)
tile(100, 510, "#545B64", "TV", "Projector", "screen view", round_=True)
tile(100, 700, "#24292F", "GitHub", "GitHub", "repo + Actions")

# public subnet
tile(345, 380, NET, "ALB", "Application LB", "HTTP + WebSocket")
add('<text x="345" y="454" class="tsub">idle timeout 3600 s</text>')
tile(345, 660, NET, "NAT", "NAT gateway", "egress")

# namespace
tile(560, 340, K8S, "pod", "liveask pod", "API · WS hub")
tile(560, 460, K8S, "pod", "liveask pod", "+ initContainer")
tile(740, 510, K8S, "cron", "cleanup", "CronJob · nightly")
tile(850, 510, K8S, "cfg", "ConfigMap", "+ Secret")
pill(758, 418, 128, "HPA 2–6 · PDB", K8S)

# add-ons
add('<text x="490" y="608" class="section">Add-ons (Helm, via Terraform)</text>')
pill(490, 620, 196, "AWS LB Controller", CMP)
pill(696, 620, 196, "metrics-server", K8S)
pill(490, 656, 196, "Deployment · Service", K8S)
pill(696, 656, 196, "Ingress (ALB class)", K8S)
pill(490, 692, 196, "Rolling update · preStop", K8S)
pill(696, 692, 196, "Probes · non-root", K8S)

# database
tile(1036, 380, DB, "RDS", "PostgreSQL 17", "LISTEN / NOTIFY")
add('<text x="1036" y="462" class="tsub">encrypted · private</text>')
add('<text x="1036" y="477" class="tsub">password in Secrets Mgr</text>')

# regional services
tile(1250, 290, SEC, "SM", "Secrets Manager", "RDS password")
tile(1250, 470, FIN, "$", "AWS Budgets", "email alerts")
tile(1250, 690, CMP, "ECR", "Amazon ECR", "immutable SHA tags")

# ---------------------------------------------------------------- labels
tag(232, 450, "HTTP + WebSocket", REQ)
tag(452, 380, "/ · /api · /ws", REQ)
tag(830, 395, "SQL + pg_notify (same transaction)", DATA)
tag(820, 268, "NOTIFY → every pod", DATA)
tag(1060, 690, "pull images", CMP)
tag(420, 796, "push → CI → OIDC → ECR", OPS)
tag(820, 776, "kubectl apply -k", OPS)

step(160, 380, "1", REQ)
step(400, 356, "2", REQ)
step(950, 395, "3", DATA)
step(1004, 326, "4", DATA)

# ---------------------------------------------------------------- legend
ly = 868
add(f'<text x="40" y="{ly}" class="legend-h">Flow</text>')
legend = [
    (REQ, False, "1–2  Clients → ALB → any liveask pod"),
    (DATA, False, "3  Write to PostgreSQL + pg_notify"),
    (DATA, True, "4  NOTIFY fans out to every pod → its WebSocket clients"),
    (OPS, False, "Delivery: GitHub Actions → ECR → EKS"),
]
x = 90
for color, dashed, text in legend:
    da = ' stroke-dasharray="6 5"' if dashed else ""
    add(f'<path d="M{x},{ly - 4} H{x + 30}" stroke="{color}" stroke-width="2.4"{da} marker-end="url(#a-{color.strip("#")})"/>')
    add(f'<text x="{x + 38}" y="{ly}" class="legend">{esc(text)}</text>')
    x += 38 + len(text) * 6.4 + 34

# ---------------------------------------------------------------- assemble
colors = {REQ, DATA, OPS, CMP, INK}
markers = "".join(
    f'<marker id="a-{c.strip("#")}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    for c in sorted(colors)
)
style = f"""
text {{ font-family: 'Amazon Ember', 'Segoe UI', Helvetica, Arial, sans-serif; }}
.title {{ font-size: 26px; font-weight: 700; fill: {INK}; }}
.subtitle {{ font-size: 14px; fill: {MUTED}; }}
.glabel {{ font-size: 12px; font-weight: 700; fill: #fff; }}
.glyph {{ font-weight: 700; fill: #fff; text-anchor: middle; }}
.tlabel {{ font-size: 13px; font-weight: 600; fill: {INK}; text-anchor: middle; }}
.tsub {{ font-size: 11px; fill: {MUTED}; text-anchor: middle; }}
.pill {{ font-size: 12px; fill: {INK}; }}
.section {{ font-size: 11px; font-weight: 700; fill: {MUTED}; letter-spacing: .5px; text-transform: uppercase; }}
.tag {{ font-size: 11px; font-weight: 600; text-anchor: middle; }}
.step {{ font-size: 12px; font-weight: 700; fill: #fff; text-anchor: middle; }}
.legend-h {{ font-size: 12px; font-weight: 700; fill: {INK}; }}
.legend {{ font-size: 12px; fill: {INK}; }}
"""
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    f'role="img" aria-label="LiveAsk architecture on AWS">\n'
    f"<title>LiveAsk architecture on AWS</title>\n"
    f"<defs><style>{style}</style>{markers}</defs>\n" + "\n".join(out) + "\n</svg>\n"
)
target = Path(__file__).with_name("architecture.svg")
target.write_text(svg, encoding="utf-8", newline="\n")
print(f"wrote {target}")
