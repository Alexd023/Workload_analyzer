
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta
import base64

REQUIRED_COLUMNS = [
    "timestamp",
    "request_type",
    "response_time_ms",
    "cpu_usage",
    "memory_usage",
    "status_code"
]

OPTIONAL_COLUMNS = [
    "user_id",
    "request_size_kb",
    "response_size_kb",
    "server_id"
]

REQUEST_TYPES = [
    "home",
    "login",
    "search",
    "view_product",
    "add_to_cart",
    "checkout",
    "payment",
    "logout",
    "recommendations",
    "api_status"
]


def generate_synthetic_workload(
    total_requests: int,
    hours: int,
    workload_type: str,
    error_rate: float,
    start_time: datetime
) -> pd.DataFrame:
    """
    Generează un workload sintetic realist pentru un sistem web / magazin online.

    Ideea este ca aplicația să poată fi demonstrată chiar și fără log-uri reale.
    Datele generate includ:
    - timestamp
    - tip cerere
    - timp răspuns
    - CPU
    - memorie
    - status code
    - user_id
    - dimensiune request/response
    - server_id
    """

    end_time = start_time + timedelta(hours=hours)
    total_seconds = int((end_time - start_time).total_seconds())

    timestamps = []

    if workload_type == "Constant":
        seconds = np.random.uniform(0, total_seconds, total_requests)

    elif workload_type == "Cu vârfuri":
        # 65% cereri normale, 35% concentrate în zona de vârf.
        normal_count = int(total_requests * 0.65)
        peak_count = total_requests - normal_count

        normal_seconds = np.random.uniform(0, total_seconds, normal_count)

        peak_start = int(total_seconds * 0.70)
        peak_end = int(total_seconds * 0.85)
        peak_seconds = np.random.uniform(peak_start, peak_end, peak_count)

        seconds = np.concatenate([normal_seconds, peak_seconds])

    elif workload_type == "Periodic":
        # Mai multe valuri de încărcare, ca într-o zi de utilizare reală.
        seconds = []
        for _ in range(total_requests):
            hour = np.random.choice(
                np.arange(hours),
                p=_periodic_hour_probabilities(hours)
            )
            sec = hour * 3600 + np.random.uniform(0, 3600)
            seconds.append(sec)
        seconds = np.array(seconds)

    else:
        seconds = np.random.uniform(0, total_seconds, total_requests)

    seconds = np.sort(seconds)
    timestamps = [start_time + timedelta(seconds=float(s)) for s in seconds]

    request_probabilities = {
        "home": 0.12,
        "login": 0.08,
        "search": 0.24,
        "view_product": 0.22,
        "add_to_cart": 0.10,
        "checkout": 0.07,
        "payment": 0.04,
        "logout": 0.04,
        "recommendations": 0.07,
        "api_status": 0.02
    }

    request_types = np.random.choice(
        list(request_probabilities.keys()),
        size=total_requests,
        p=list(request_probabilities.values())
    )

    base_response = {
        "home": 100,
        "login": 180,
        "search": 380,
        "view_product": 230,
        "add_to_cart": 300,
        "checkout": 700,
        "payment": 950,
        "logout": 90,
        "recommendations": 520,
        "api_status": 60
    }

    # Estimăm o încărcare temporală pentru fiecare minut, apoi o folosim ca factor de degradare.
    tmp = pd.DataFrame({"timestamp": timestamps})
    tmp["minute"] = pd.to_datetime(tmp["timestamp"]).dt.floor("min")
    per_minute = tmp.groupby("minute").size()
    per_minute_norm = (per_minute - per_minute.min()) / max(1, (per_minute.max() - per_minute.min()))
    minute_load = per_minute_norm.to_dict()

    response_times = []
    cpu_usage = []
    memory_usage = []
    status_codes = []
    request_size = []
    response_size = []

    for ts, rt in zip(timestamps, request_types):
        minute = pd.to_datetime(ts).floor("min")
        load_factor = minute_load.get(minute, 0)

        noise = np.random.lognormal(mean=0, sigma=0.35)
        response = base_response[rt] * noise * (1 + 1.4 * load_factor)

        # Unele cereri lente rare.
        if np.random.random() < 0.015:
            response *= np.random.uniform(2.5, 5.0)

        response = max(20, response)
        response_times.append(round(response, 2))

        cpu = 20 + 65 * load_factor + (response / 2500) * 18 + np.random.normal(0, 5)
        cpu = float(np.clip(cpu, 5, 99))
        cpu_usage.append(round(cpu, 2))

        mem = 35 + 25 * load_factor + np.random.normal(0, 4)
        if rt in ["search", "recommendations", "checkout", "payment"]:
            mem += np.random.uniform(3, 12)
        mem = float(np.clip(mem, 10, 96))
        memory_usage.append(round(mem, 2))

        effective_error_rate = error_rate / 100
        if response > 1500:
            effective_error_rate += 0.02
        if cpu > 85:
            effective_error_rate += 0.03

        if np.random.random() < effective_error_rate:
            status_codes.append(np.random.choice([400, 404, 500, 502, 503], p=[0.20, 0.15, 0.35, 0.15, 0.15]))
        else:
            status_codes.append(np.random.choice([200, 201, 204], p=[0.92, 0.05, 0.03]))

        request_size.append(round(np.random.lognormal(mean=2.6, sigma=0.55), 2))
        response_size.append(round(np.random.lognormal(mean=4.0, sigma=0.65), 2))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "request_type": request_types,
        "response_time_ms": response_times,
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "status_code": status_codes,
        "user_id": np.random.randint(1, max(30, total_requests // 20), total_requests),
        "request_size_kb": request_size,
        "response_size_kb": response_size,
        "server_id": np.random.choice(["srv-1", "srv-2", "srv-3"], total_requests)
    })

    return df.sort_values("timestamp").reset_index(drop=True)


def _periodic_hour_probabilities(hours: int) -> np.ndarray:
    x = np.arange(hours)
    # Model simplu cu vârfuri aproximative dimineața, la prânz și seara.
    p = (
        0.45 * np.exp(-((x - hours * 0.30) ** 2) / (2 * (hours * 0.08) ** 2)) +
        0.35 * np.exp(-((x - hours * 0.55) ** 2) / (2 * (hours * 0.10) ** 2)) +
        0.70 * np.exp(-((x - hours * 0.78) ** 2) / (2 * (hours * 0.08) ** 2)) +
        0.05
    )
    return p / p.sum()


def validate_and_preprocess(df: pd.DataFrame):
    errors = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"Lipsesc coloanele obligatorii: {', '.join(missing)}")
        return None, errors

    df = df.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["response_time_ms", "cpu_usage", "memory_usage", "status_code"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    removed = before - len(df)

    if removed > 0:
        errors.append(f"Au fost eliminate {removed} rânduri invalide sau incomplete.")

    df = df.sort_values("timestamp").reset_index(drop=True)
    df["minute"] = df["timestamp"].dt.floor("min")
    df["hour"] = df["timestamp"].dt.floor("h")
    df["is_error"] = df["status_code"] >= 400
    df["is_success"] = ~df["is_error"]

    return df, errors


def compute_general_metrics(df: pd.DataFrame) -> dict:
    start = df["timestamp"].min()
    end = df["timestamp"].max()
    duration_minutes = max(1, (end - start).total_seconds() / 60)

    per_minute = df.groupby("minute").size()

    metrics = {
        "total_requests": int(len(df)),
        "duration_minutes": duration_minutes,
        "duration_hours": duration_minutes / 60,
        "avg_requests_per_minute": len(df) / duration_minutes,
        "peak_requests_per_minute": int(per_minute.max()) if len(per_minute) else 0,
        "avg_response_time": float(df["response_time_ms"].mean()),
        "median_response_time": float(df["response_time_ms"].median()),
        "p90_response_time": float(df["response_time_ms"].quantile(0.90)),
        "p95_response_time": float(df["response_time_ms"].quantile(0.95)),
        "p99_response_time": float(df["response_time_ms"].quantile(0.99)),
        "error_rate": float(df["is_error"].mean() * 100),
        "avg_cpu": float(df["cpu_usage"].mean()),
        "avg_memory": float(df["memory_usage"].mean()),
        "max_cpu": float(df["cpu_usage"].max()),
        "max_memory": float(df["memory_usage"].max()),
        "start": start,
        "end": end
    }

    metrics["workload_intensity_score"] = compute_intensity_score(metrics)

    return metrics


def compute_intensity_score(m: dict) -> float:
    """
    Scor orientativ 0-100 pentru intensitatea workload-ului.

    Formula combină:
    - încărcarea medie;
    - diferența dintre vârf și medie;
    - latența P95;
    - utilizarea CPU;
    - rata de eroare.

    Observație:
    Formula nu este una universală, ci un indicator agregat folosit pentru comparație
    între scenarii de workload. Un workload cu vârfuri trebuie să primească un scor
    mai mare decât unul constant, dacă restul indicatorilor sunt similari.
    """
    avg_rpm = m["avg_requests_per_minute"]
    peak_rpm = m["peak_requests_per_minute"]
    peak_ratio = peak_rpm / max(1, avg_rpm)

    avg_load_component = min(20, avg_rpm / 2)
    peak_component = min(20, max(0, peak_ratio - 1) * 10)
    latency_component = min(25, m["p95_response_time"] / 80)
    cpu_component = min(20, m["avg_cpu"] / 4)
    error_component = min(15, m["error_rate"] * 3)

    score = (
        avg_load_component +
        peak_component +
        latency_component +
        cpu_component +
        error_component
    )

    return round(float(min(100, score)), 2)


def analyze_by_request_type(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("request_type").agg(
        requests=("request_type", "count"),
        percentage=("request_type", lambda x: len(x) / len(df) * 100),
        avg_response_ms=("response_time_ms", "mean"),
        median_response_ms=("response_time_ms", "median"),
        p95_response_ms=("response_time_ms", lambda x: x.quantile(0.95)),
        p99_response_ms=("response_time_ms", lambda x: x.quantile(0.99)),
        error_rate_percent=("is_error", lambda x: x.mean() * 100),
        avg_cpu=("cpu_usage", "mean"),
        avg_memory=("memory_usage", "mean")
    ).reset_index()

    return grouped.sort_values("requests", ascending=False)


def time_series_analysis(df: pd.DataFrame) -> pd.DataFrame:
    ts = df.groupby("minute").agg(
        requests=("request_type", "count"),
        avg_response_ms=("response_time_ms", "mean"),
        p95_response_ms=("response_time_ms", lambda x: x.quantile(0.95)),
        error_rate_percent=("is_error", lambda x: x.mean() * 100),
        avg_cpu=("cpu_usage", "mean"),
        avg_memory=("memory_usage", "mean")
    ).reset_index()

    return ts


def detect_anomalies(df: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    anomalies = []

    q1 = df["response_time_ms"].quantile(0.25)
    q3 = df["response_time_ms"].quantile(0.75)
    iqr = q3 - q1
    slow_threshold = q3 + 1.5 * iqr

    slow_count = int((df["response_time_ms"] > slow_threshold).sum())
    if slow_count > 0:
        anomalies.append({
            "tip": "Cereri lente",
            "descriere": f"{slow_count} cereri au depășit pragul de {slow_threshold:.2f} ms.",
            "severitate": "medie" if slow_count / len(df) < 0.05 else "ridicată"
        })

    if len(ts) > 1:
        req_mean = ts["requests"].mean()
        req_std = ts["requests"].std()
        req_threshold = req_mean + 2 * req_std
        peak_rows = ts[ts["requests"] > req_threshold]

        if not peak_rows.empty:
            anomalies.append({
                "tip": "Vârf de încărcare",
                "descriere": f"{len(peak_rows)} minute au depășit pragul de {req_threshold:.2f} cereri/minut.",
                "severitate": "ridicată"
            })

        err_mean = ts["error_rate_percent"].mean()
        err_std = ts["error_rate_percent"].std()
        err_threshold = err_mean + 2 * err_std
        err_rows = ts[(ts["error_rate_percent"] > err_threshold) & (ts["error_rate_percent"] > 1)]

        if not err_rows.empty:
            anomalies.append({
                "tip": "Creștere rată erori",
                "descriere": f"{len(err_rows)} minute au avut rată de eroare neobișnuit de mare.",
                "severitate": "ridicată"
            })

    high_cpu = df[df["cpu_usage"] > 90]
    if not high_cpu.empty:
        anomalies.append({
            "tip": "CPU ridicat",
            "descriere": f"{len(high_cpu)} cereri au fost procesate când CPU-ul era peste 90%.",
            "severitate": "ridicată"
        })

    if not anomalies:
        anomalies.append({
            "tip": "Fără anomalii majore",
            "descriere": "Nu au fost detectate deviații semnificative față de comportamentul general.",
            "severitate": "scăzută"
        })

    return pd.DataFrame(anomalies)


def classify_workload(df: pd.DataFrame, metrics: dict, type_stats: pd.DataFrame, ts: pd.DataFrame) -> dict:
    classifications = []

    requests_mean = ts["requests"].mean()
    requests_std = ts["requests"].std() if len(ts) > 1 else 0
    cv = requests_std / requests_mean if requests_mean else 0

    peak_ratio = metrics["peak_requests_per_minute"] / max(1, metrics["avg_requests_per_minute"])
    top_type_percentage = float(type_stats["percentage"].max()) if not type_stats.empty else 0

    corr_req_resp = ts["requests"].corr(ts["avg_response_ms"]) if len(ts) > 2 else np.nan
    corr_cpu_resp = df["cpu_usage"].corr(df["response_time_ms"]) if len(df) > 2 else np.nan

    if cv < 0.35:
        classifications.append("workload relativ constant")
    elif cv < 0.90:
        classifications.append("workload variabil")
    else:
        classifications.append("workload cu vârfuri pronunțate")

    if peak_ratio >= 3:
        classifications.append("prezintă perioade de vârf semnificative")

    if top_type_percentage >= 50:
        classifications.append("distribuție dezechilibrată a tipurilor de cereri")
    elif top_type_percentage >= 30:
        classifications.append("distribuție moderat dezechilibrată a tipurilor de cereri")
    else:
        classifications.append("distribuție relativ echilibrată a tipurilor de cereri")

    if not np.isnan(corr_req_resp) and corr_req_resp > 0.55:
        classifications.append("risc de degradare a timpului de răspuns la creșterea volumului")

    if not np.isnan(corr_cpu_resp) and corr_cpu_resp > 0.55:
        classifications.append("timpul de răspuns este puternic influențat de utilizarea CPU")

    return {
        "summary": ", ".join(classifications),
        "coefficient_of_variation": float(cv),
        "peak_ratio": float(peak_ratio),
        "top_type_percentage": float(top_type_percentage),
        "corr_requests_response": None if np.isnan(corr_req_resp) else float(corr_req_resp),
        "corr_cpu_response": None if np.isnan(corr_cpu_resp) else float(corr_cpu_resp)
    }


def generate_conclusions(metrics: dict, type_stats: pd.DataFrame, classification: dict, anomalies: pd.DataFrame) -> list:
    conclusions = []

    dominant = type_stats.iloc[0]
    slowest = type_stats.sort_values("p95_response_ms", ascending=False).iloc[0]
    most_errors = type_stats.sort_values("error_rate_percent", ascending=False).iloc[0]

    conclusions.append(
        f"Au fost analizate {metrics['total_requests']:,} cereri pe o perioadă de "
        f"{metrics['duration_hours']:.2f} ore."
    )

    conclusions.append(
        f"Volumul mediu este de {metrics['avg_requests_per_minute']:.2f} cereri/minut, "
        f"iar vârful maxim este de {metrics['peak_requests_per_minute']} cereri/minut."
    )

    conclusions.append(
        f"Workload-ul poate fi caracterizat ca: {classification['summary']}."
    )

    conclusions.append(
        f"Operația dominantă este '{dominant['request_type']}', reprezentând "
        f"{dominant['percentage']:.2f}% din totalul cererilor."
    )

    conclusions.append(
        f"Cea mai lentă operație după P95 este '{slowest['request_type']}', "
        f"cu P95 = {slowest['p95_response_ms']:.2f} ms."
    )

    conclusions.append(
        f"Cea mai mare rată de eroare apare la '{most_errors['request_type']}', "
        f"cu {most_errors['error_rate_percent']:.2f}%."
    )

    conclusions.append(
        f"Timpul mediu de răspuns este {metrics['avg_response_time']:.2f} ms, "
        f"iar P95 este {metrics['p95_response_time']:.2f} ms. "
        "P95 este mai relevant decât media pentru a observa experiența utilizatorilor afectați de întârzieri."
    )

    if metrics["avg_cpu"] > 75:
        conclusions.append("Utilizarea medie CPU este ridicată, ceea ce poate indica un risc de bottleneck.")
    elif metrics["avg_cpu"] > 55:
        conclusions.append("Utilizarea CPU este moderată spre ridicată și trebuie urmărită în perioadele de vârf.")
    else:
        conclusions.append("Utilizarea CPU este în general acceptabilă.")

    if metrics["error_rate"] > 5:
        conclusions.append("Rata de eroare este ridicată și indică probleme de stabilitate în workload-ul analizat.")
    elif metrics["error_rate"] > 1:
        conclusions.append("Rata de eroare este moderată și trebuie investigată pe tipuri de cereri.")
    else:
        conclusions.append("Rata de eroare este scăzută.")

    high_severity = anomalies[anomalies["severitate"] == "ridicată"]
    if not high_severity.empty:
        conclusions.append("Au fost detectate anomalii importante care trebuie investigate: " + ", ".join(high_severity["tip"].tolist()) + ".")

    return conclusions


def create_html_report(metrics, type_stats, classification, anomalies, conclusions):
    type_table = type_stats.round(2).to_html(index=False)
    anomaly_table = anomalies.to_html(index=False)

    conclusions_html = "".join([f"<li>{c}</li>" for c in conclusions])

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Raport Workload Analyzer</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; }}
            h1, h2 {{ color: #222; }}
            .metric {{ padding: 8px; background: #f2f2f2; margin: 6px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
            th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
            th {{ background: #eee; }}
        </style>
    </head>
    <body>
        <h1>Raport de caracterizare a volumului de lucru</h1>

        <h2>1. Indicatori generali</h2>
        <div class="metric">Total cereri: {metrics['total_requests']:,}</div>
        <div class="metric">Durată analizată: {metrics['duration_hours']:.2f} ore</div>
        <div class="metric">Rată medie: {metrics['avg_requests_per_minute']:.2f} cereri/minut</div>
        <div class="metric">Vârf maxim: {metrics['peak_requests_per_minute']} cereri/minut</div>
        <div class="metric">Timp mediu răspuns: {metrics['avg_response_time']:.2f} ms</div>
        <div class="metric">P95: {metrics['p95_response_time']:.2f} ms</div>
        <div class="metric">P99: {metrics['p99_response_time']:.2f} ms</div>
        <div class="metric">Rată erori: {metrics['error_rate']:.2f}%</div>
        <div class="metric">CPU mediu: {metrics['avg_cpu']:.2f}%</div>
        <div class="metric">Memorie medie: {metrics['avg_memory']:.2f}%</div>
        <div class="metric">Scor de intensitate workload: {metrics['workload_intensity_score']}/100</div>

        <h2>2. Clasificare workload</h2>
        <p>{classification['summary']}</p>

        <h2>3. Analiză pe tipuri de cereri</h2>
        {type_table}

        <h2>4. Anomalii detectate</h2>
        {anomaly_table}

        <h2>5. Concluzii generate automat</h2>
        <ul>{conclusions_html}</ul>
    </body>
    </html>
    """

    return html


def create_pdf_report(metrics, type_stats, classification, anomalies, conclusions):
    """
    Creează un PDF simplu. Dacă reportlab nu este instalat, aplicația va afișa instrucțiuni.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except Exception:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Raport de caracterizare a volumului de lucru", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Indicatori generali", styles["Heading2"]))
    metrics_data = [
        ["Total cereri", f"{metrics['total_requests']:,}"],
        ["Durată analizată", f"{metrics['duration_hours']:.2f} ore"],
        ["Rată medie", f"{metrics['avg_requests_per_minute']:.2f} cereri/minut"],
        ["Vârf maxim", f"{metrics['peak_requests_per_minute']} cereri/minut"],
        ["Timp mediu răspuns", f"{metrics['avg_response_time']:.2f} ms"],
        ["P95", f"{metrics['p95_response_time']:.2f} ms"],
        ["P99", f"{metrics['p99_response_time']:.2f} ms"],
        ["Rată erori", f"{metrics['error_rate']:.2f}%"],
        ["CPU mediu", f"{metrics['avg_cpu']:.2f}%"],
        ["Memorie medie", f"{metrics['avg_memory']:.2f}%"],
        ["Scor intensitate", f"{metrics['workload_intensity_score']}/100"],
    ]
    t = Table(metrics_data)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("2. Clasificare workload", styles["Heading2"]))
    story.append(Paragraph(classification["summary"], styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. Concluzii", styles["Heading2"]))
    for c in conclusions:
        story.append(Paragraph("• " + c, styles["BodyText"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 12))
    story.append(Paragraph("4. Top tipuri de cereri", styles["Heading2"]))
    mini = type_stats.head(8).copy()
    mini = mini[["request_type", "requests", "percentage", "avg_response_ms", "p95_response_ms", "error_rate_percent"]].round(2)
    table_data = [mini.columns.tolist()] + mini.astype(str).values.tolist()
    tt = Table(table_data)
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(tt)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def fig_to_bytes(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf


def compare_workloads(df1, df2):
    m1 = compute_general_metrics(df1)
    m2 = compute_general_metrics(df2)

    rows = [
        ["Total cereri", m1["total_requests"], m2["total_requests"]],
        ["Cereri/minut", m1["avg_requests_per_minute"], m2["avg_requests_per_minute"]],
        ["Vârf cereri/minut", m1["peak_requests_per_minute"], m2["peak_requests_per_minute"]],
        ["Timp mediu răspuns", m1["avg_response_time"], m2["avg_response_time"]],
        ["P95", m1["p95_response_time"], m2["p95_response_time"]],
        ["P99", m1["p99_response_time"], m2["p99_response_time"]],
        ["Rată erori", m1["error_rate"], m2["error_rate"]],
        ["CPU mediu", m1["avg_cpu"], m2["avg_cpu"]],
        ["Memorie medie", m1["avg_memory"], m2["avg_memory"]],
        ["Scor intensitate", m1["workload_intensity_score"], m2["workload_intensity_score"]],
    ]

    comp = pd.DataFrame(rows, columns=["Indicator", "Workload A", "Workload B"])
    comp["Diferență B - A"] = comp["Workload B"] - comp["Workload A"]
    comp["Creștere procentuală"] = np.where(
        comp["Workload A"] != 0,
        (comp["Diferență B - A"] / comp["Workload A"]) * 100,
        np.nan
    )

    return comp


def main():
    st.set_page_config(
        page_title="Workload Analyzer",
        layout="wide"
    )

    st.title("Workload Analyzer")
    st.caption("Aplicație pentru caracterizarea volumului de lucru și evaluarea performanței unui sistem software")

    st.sidebar.header("Sursă date")
    data_source = st.sidebar.radio(
        "Alege sursa datelor:",
        ["Generează workload sintetic", "Încarcă CSV"]
    )

    df_raw = None

    if data_source == "Generează workload sintetic":
        st.sidebar.subheader("Parametri workload")
        total_requests = st.sidebar.slider("Număr cereri", 1_000, 200_000, 50_000, step=1_000)
        hours = st.sidebar.slider("Durată simulare, ore", 1, 72, 24)
        workload_type = st.sidebar.selectbox("Tip workload", ["Constant", "Cu vârfuri", "Periodic"])
        error_rate = st.sidebar.slider("Rată de eroare inițială (%)", 0.0, 15.0, 2.0, step=0.5)
        start_time = st.sidebar.datetime_input("Moment start", datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

        if st.sidebar.button("Generează date"):
            df_raw = generate_synthetic_workload(total_requests, hours, workload_type, error_rate, start_time)
            st.session_state["df_raw"] = df_raw

        if "df_raw" in st.session_state:
            df_raw = st.session_state["df_raw"]

    else:
        uploaded = st.sidebar.file_uploader("Încarcă fișier CSV", type=["csv"])
        if uploaded is not None:
            df_raw = pd.read_csv(uploaded)

    if df_raw is None:
        st.info("Generează un workload sintetic sau încarcă un fișier CSV pentru a începe analiza.")
        st.markdown("""
        Coloane obligatorii pentru CSV:
        `timestamp`, `request_type`, `response_time_ms`, `cpu_usage`, `memory_usage`, `status_code`.

        Coloane opționale:
        `user_id`, `request_size_kb`, `response_size_kb`, `server_id`.
        """)
        return

    df, validation_messages = validate_and_preprocess(df_raw)

    if df is None:
        st.error("Fișierul nu poate fi analizat.")
        for msg in validation_messages:
            st.warning(msg)
        return

    for msg in validation_messages:
        st.warning(msg)

    metrics = compute_general_metrics(df)
    type_stats = analyze_by_request_type(df)
    ts = time_series_analysis(df)
    anomalies = detect_anomalies(df, ts)
    classification = classify_workload(df, metrics, type_stats, ts)
    conclusions = generate_conclusions(metrics, type_stats, classification, anomalies)

    tabs = st.tabs([
        "Dashboard",
        "Compoziție workload",
        "Analiză temporală",
        "Corelații",
        "Anomalii",
        "Comparație",
        "Raport"
    ])

    with tabs[0]:
        st.header("Dashboard general")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total cereri", f"{metrics['total_requests']:,}")
        c2.metric("Durată", f"{metrics['duration_hours']:.2f} h")
        c3.metric("Cereri/minut", f"{metrics['avg_requests_per_minute']:.2f}")
        c4.metric("Vârf cereri/minut", f"{metrics['peak_requests_per_minute']}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Timp mediu", f"{metrics['avg_response_time']:.2f} ms")
        c6.metric("P95", f"{metrics['p95_response_time']:.2f} ms")
        c7.metric("Rată erori", f"{metrics['error_rate']:.2f}%")
        c8.metric("Scor intensitate", f"{metrics['workload_intensity_score']}/100")

        c9, c10 = st.columns(2)
        c9.metric("CPU mediu", f"{metrics['avg_cpu']:.2f}%")
        c10.metric("Memorie medie", f"{metrics['avg_memory']:.2f}%")

        st.subheader("Clasificare automată")
        st.success(classification["summary"])

        st.subheader("Primele rânduri din date")
        st.dataframe(df.head(50), use_container_width=True)

    with tabs[1]:
        st.header("Compoziția volumului de lucru")

        st.subheader("Statistici pe tipuri de cereri")
        st.dataframe(type_stats.round(2), use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Distribuția cererilor pe tip")
            fig, ax = plt.subplots()
            type_stats.sort_values("requests", ascending=True).plot(
                x="request_type", y="requests", kind="barh", ax=ax, legend=False
            )
            ax.set_xlabel("Număr cereri")
            ax.set_ylabel("Tip cerere")
            st.pyplot(fig)

        with col2:
            st.subheader("Cele mai lente operații după P95")
            slow = type_stats.sort_values("p95_response_ms", ascending=True)
            fig, ax = plt.subplots()
            slow.plot(x="request_type", y="p95_response_ms", kind="barh", ax=ax, legend=False)
            ax.set_xlabel("P95 response time, ms")
            ax.set_ylabel("Tip cerere")
            st.pyplot(fig)

    with tabs[2]:
        st.header("Analiză temporală")

        st.subheader("Cereri pe minut")
        st.line_chart(ts.set_index("minute")["requests"])

        st.subheader("Timp mediu de răspuns și P95 în timp")
        st.line_chart(ts.set_index("minute")[["avg_response_ms", "p95_response_ms"]])

        st.subheader("CPU și memorie în timp")
        st.line_chart(ts.set_index("minute")[["avg_cpu", "avg_memory"]])

        st.subheader("Rată erori în timp")
        st.line_chart(ts.set_index("minute")["error_rate_percent"])

        st.subheader("Intervale cu încărcare maximă")
        st.dataframe(ts.sort_values("requests", ascending=False).head(10).round(2), use_container_width=True)

    with tabs[3]:
        st.header("Corelații și relația workload-performanță")

        corr_req_resp = classification["corr_requests_response"]
        corr_cpu_resp = classification["corr_cpu_response"]

        c1, c2 = st.columns(2)
        c1.metric("Corelație cereri/minut - timp răspuns", "N/A" if corr_req_resp is None else f"{corr_req_resp:.3f}")
        c2.metric("Corelație CPU - timp răspuns", "N/A" if corr_cpu_resp is None else f"{corr_cpu_resp:.3f}")

        st.subheader("Cereri/minut vs timp mediu de răspuns")
        fig, ax = plt.subplots()
        ax.scatter(ts["requests"], ts["avg_response_ms"])
        ax.set_xlabel("Cereri/minut")
        ax.set_ylabel("Timp mediu răspuns, ms")
        st.pyplot(fig)

        st.subheader("CPU vs timp de răspuns")
        sample = df.sample(min(len(df), 5000), random_state=42)
        fig, ax = plt.subplots()
        ax.scatter(sample["cpu_usage"], sample["response_time_ms"], alpha=0.35)
        ax.set_xlabel("CPU usage, %")
        ax.set_ylabel("Response time, ms")
        st.pyplot(fig)

        st.subheader("Matrice de corelație")
        corr_cols = ["response_time_ms", "cpu_usage", "memory_usage", "status_code"]
        if "request_size_kb" in df.columns:
            corr_cols.append("request_size_kb")
        if "response_size_kb" in df.columns:
            corr_cols.append("response_size_kb")
        st.dataframe(df[corr_cols].corr().round(3), use_container_width=True)

    with tabs[4]:
        st.header("Detectare anomalii")

        st.dataframe(anomalies, use_container_width=True)

        st.subheader("Distribuția timpilor de răspuns")
        fig, ax = plt.subplots()
        ax.hist(df["response_time_ms"], bins=50)
        ax.set_xlabel("Response time, ms")
        ax.set_ylabel("Frecvență")
        st.pyplot(fig)

        st.subheader("Cereri cu cei mai mari timpi de răspuns")
        st.dataframe(
            df.sort_values("response_time_ms", ascending=False).head(25),
            use_container_width=True
        )

    with tabs[5]:
        st.header("Comparație între două workload-uri")
        st.write("Încarcă un al doilea CSV pentru a compara workload-ul curent cu alt scenariu, de exemplu normal vs vârf.")

        uploaded_b = st.file_uploader("CSV workload B", type=["csv"], key="compare_b")

        if uploaded_b is not None:
            df_b_raw = pd.read_csv(uploaded_b)
            df_b, errors_b = validate_and_preprocess(df_b_raw)
            if df_b is None:
                st.error("Workload B nu este valid.")
                for e in errors_b:
                    st.warning(e)
            else:
                comp = compare_workloads(df, df_b)
                st.dataframe(comp.round(2), use_container_width=True)

                st.download_button(
                    "Descarcă comparația CSV",
                    comp.to_csv(index=False).encode("utf-8"),
                    "comparatie_workload.csv",
                    "text/csv"
                )
        else:
            st.info("Pentru comparație, încarcă un al doilea fișier CSV valid.")

    with tabs[6]:
        st.header("Raport și concluzii")

        st.subheader("Concluzii generate automat")
        for c in conclusions:
            st.write("- " + c)

        html_report = create_html_report(metrics, type_stats, classification, anomalies, conclusions)
        st.download_button(
            "Descarcă raport HTML",
            html_report.encode("utf-8"),
            "raport_workload_analyzer.html",
            "text/html"
        )

        pdf_bytes = create_pdf_report(metrics, type_stats, classification, anomalies, conclusions)
        if pdf_bytes is not None:
            st.download_button(
                "Descarcă raport PDF",
                pdf_bytes,
                "raport_workload_analyzer.pdf",
                "application/pdf"
            )
        else:
            st.warning("Pentru export PDF instalează dependența reportlab: pip install reportlab")

        st.download_button(
            "Descarcă datele preprocesate CSV",
            df.to_csv(index=False).encode("utf-8"),
            "workload_preprocesat.csv",
            "text/csv"
        )

        st.download_button(
            "Descarcă statistici pe tipuri CSV",
            type_stats.to_csv(index=False).encode("utf-8"),
            "statistici_tipuri_cereri.csv",
            "text/csv"
        )


if __name__ == "__main__":
    main()
