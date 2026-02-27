from flask import Flask, render_template, request, send_file, send_from_directory, abort, jsonify
import pandas as pd
import os
import calendar
import uuid
import shutil
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CHART_HISTORY_FILE = os.path.join(BASE_DIR, "chart_history.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")


def normalize_storage_path(path_value, fallback_name):
    if not path_value:
        return os.path.join(BASE_DIR, fallback_name)

    cleaned = path_value.strip()
    if not cleaned:
        return os.path.join(BASE_DIR, fallback_name)

    if os.path.isabs(cleaned):
        return os.path.abspath(cleaned)

    return os.path.abspath(os.path.join(BASE_DIR, cleaned))


def load_storage_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "upload_folder": os.path.join(BASE_DIR, "uploads"),
            "output_folder": os.path.join(BASE_DIR, "output"),
        }

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except Exception:
        data = {}

    return {
        "upload_folder": normalize_storage_path(data.get("upload_folder"), "uploads"),
        "output_folder": normalize_storage_path(data.get("output_folder"), "output"),
    }


def save_storage_config(upload_folder, output_folder):
    config_data = {
        "upload_folder": upload_folder,
        "output_folder": output_folder,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file, indent=2)


def apply_storage_paths(upload_folder, output_folder):
    global UPLOAD_FOLDER, OUTPUT_FOLDER
    UPLOAD_FOLDER = upload_folder
    OUTPUT_FOLDER = output_folder
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def get_directory_roots():
    if os.name == "nt":
        roots = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append(drive)
        return roots
    return [os.path.abspath(os.sep)]


def get_quick_access_path(path_type):
    """Get common quick access paths (Desktop, Documents, Downloads, Project)"""
    user_home = os.path.expanduser("~")
    
    paths = {
        "desktop": os.path.join(user_home, "Desktop"),
        "documents": os.path.join(user_home, "Documents"),
        "downloads": os.path.join(user_home, "Downloads"),
        "home": user_home,
        "project": BASE_DIR,
    }
    
    # Windows-specific paths
    if os.name == "nt":
        # Try to get actual Windows paths from environment
        desktop = os.environ.get("USERPROFILE", user_home)
        paths["desktop"] = os.path.join(desktop, "Desktop")
        paths["documents"] = os.path.join(desktop, "Documents")
        paths["downloads"] = os.path.join(desktop, "Downloads")
    
    requested_path = paths.get(path_type.lower())
    if requested_path and os.path.isdir(requested_path):
        return requested_path
    return None


def load_chart_history():
    if not os.path.exists(CHART_HISTORY_FILE):
        return []
    try:
        with open(CHART_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_chart_to_history(labels, values, revenue, product, time_mode, filename=""):
    history = load_chart_history()
    entry = {
        "id": uuid.uuid4().hex[:8],
        "timestamp": datetime.now().isoformat(),
        "labels": labels,
        "values": values,
        "revenue": float(revenue),
        "product": str(product),
        "time_mode": time_mode,
        "filename": filename,
    }
    history.insert(0, entry)
    # Keep only last 20 chart sessions
    history = history[:20]
    try:
        with open(CHART_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass
    return entry["id"]


storage_config = load_storage_config()
apply_storage_paths(storage_config["upload_folder"], storage_config["output_folder"])


def read_csv_flexible(filepath):
    try:
        return pd.read_csv(filepath, encoding="utf-8")
    except Exception:
        return pd.read_csv(filepath, encoding="latin1")


def parse_month_to_number(month_series):
    numeric = pd.to_numeric(month_series, errors="coerce")
    short_name = pd.to_datetime(month_series.astype(str), format="%b", errors="coerce").dt.month
    full_name = pd.to_datetime(month_series.astype(str), format="%B", errors="coerce").dt.month
    return numeric.fillna(short_name).fillna(full_name)


def guess_column(columns, preferred_names):
    for name in preferred_names:
        if name in columns:
            return name
    return ""


def list_reports():
    reports = []
    for filename in os.listdir(OUTPUT_FOLDER):
        if not filename.lower().endswith((".xlsx", ".pdf")):
            continue

        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue

        stat = os.stat(filepath)
        reports.append(
            {
                "name": filename,
                "size_kb": round(stat.st_size / 1024, 2),
                "updated_at": datetime.fromtimestamp(stat.st_mtime),
                "type": "Excel" if filename.lower().endswith(".xlsx") else "PDF",
            }
        )

    reports.sort(key=lambda item: item["updated_at"], reverse=True)
    return reports


def build_analytics_summary():
    reports = list_reports()
    excel_reports = [item for item in reports if item["type"] == "Excel"]
    pdf_reports = [item for item in reports if item["type"] == "PDF"]

    total_size_kb = round(sum(item["size_kb"] for item in reports), 2)
    latest_report = reports[0] if reports else None

    latest_excel_kpis = None
    if excel_reports:
        latest_excel_path = os.path.join(OUTPUT_FOLDER, excel_reports[0]["name"])
        try:
            latest_df = pd.read_excel(latest_excel_path)
            latest_df.columns = latest_df.columns.str.strip().str.lower()

            if "total" in latest_df.columns:
                latest_df["total"] = pd.to_numeric(latest_df["total"], errors="coerce")

            if "product" in latest_df.columns and "total" in latest_df.columns:
                cleaned = latest_df.dropna(subset=["product", "total"]).copy()
                if not cleaned.empty:
                    latest_excel_kpis = {
                        "rows": int(cleaned.shape[0]),
                        "total_revenue": float(cleaned["total"].sum()),
                        "top_product": cleaned.groupby("product")["total"].sum().idxmax(),
                    }
        except Exception:
            latest_excel_kpis = None

    return {
        "reports": reports,
        "total_reports": len(reports),
        "excel_reports": len(excel_reports),
        "pdf_reports": len(pdf_reports),
        "total_size_kb": total_size_kb,
        "latest_report": latest_report,
        "latest_excel_kpis": latest_excel_kpis,
    }


def build_settings_summary():
    reports = list_reports()
    excel_count = len([item for item in reports if item["type"] == "Excel"])
    pdf_count = len([item for item in reports if item["type"] == "PDF"])
    latest_report = reports[0] if reports else None

    upload_files_count = 0
    for name in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, name)
        if os.path.isfile(path):
            upload_files_count += 1

    return {
        "app_name": "AutoSales Dashboard",
        "app_version": "1.0.0",
        "environment": "Development",
        "upload_folder": os.path.abspath(UPLOAD_FOLDER),
        "output_folder": os.path.abspath(OUTPUT_FOLDER),
        "total_reports": len(reports),
        "excel_count": excel_count,
        "pdf_count": pdf_count,
        "upload_files_count": upload_files_count,
        "latest_report": latest_report,
    }


def build_admin_summary():
    reports = list_reports()
    latest_activity = reports[0]["updated_at"] if reports else None
    return {
        "name": "Admin User",
        "role": "System Administrator",
        "email": "admin@autosales.local",
        "status": "Active",
        "last_login": datetime.now(),
        "latest_activity": latest_activity,
        "managed_reports": len(reports),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action", "read_columns")

        if action == "read_columns":
            file = request.files.get("file")
            if file is None or file.filename == "":
                return render_template("index.html", error="Please upload a file first.")

            file_token = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, file_token)
            file.save(filepath)

            try:
                df_preview = read_csv_flexible(filepath)
            except Exception:
                return render_template("index.html", error="Unable to read CSV file.")

            df_preview.columns = df_preview.columns.str.strip().str.lower()
            columns = df_preview.columns.tolist()
            defaults = {
                "product_col": guess_column(columns, ["product", "item", "product_name"]),
                "total_col": guess_column(columns, ["total", "amount", "revenue", "sales"]),
                "quantity_col": guess_column(columns, ["quantity", "qty", "units"]),
                "price_col": guess_column(columns, ["price", "unit_price", "rate"]),
                "date_col": guess_column(columns, ["date", "order_date", "invoice_date"]),
                "year_col": guess_column(columns, ["year"]),
                "month_col": guess_column(columns, ["month"]),
            }

            return render_template(
                "index.html",
                columns=columns,
                file_token=file_token,
                defaults=defaults,
                selected_mode="date",
            )

        if action == "process_data":
            file_token = request.form.get("file_token", "")
            if not file_token:
                return render_template("index.html", error="Session expired. Please upload file again.")

            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(file_token))
            if not os.path.exists(filepath):
                return render_template("index.html", error="Uploaded file not found. Please upload again.")

            try:
                df = read_csv_flexible(filepath)
            except Exception:
                return render_template("index.html", error="Unable to read uploaded CSV.")

            df.columns = df.columns.str.strip().str.lower()
            columns = df.columns.tolist()

            time_mode = request.form.get("time_mode", "date").strip().lower()
            if time_mode not in {"date", "year_month", "year", "month"}:
                time_mode = "date"

            product_col = request.form.get("product_col", "").strip().lower()
            total_col = request.form.get("total_col", "").strip().lower()
            quantity_col = request.form.get("quantity_col", "").strip().lower()
            price_col = request.form.get("price_col", "").strip().lower()
            date_col = request.form.get("date_col", "").strip().lower()
            year_col = request.form.get("year_col", "").strip().lower()
            month_col = request.form.get("month_col", "").strip().lower()

            defaults = {
                "product_col": product_col,
                "total_col": total_col,
                "quantity_col": quantity_col,
                "price_col": price_col,
                "date_col": date_col,
                "year_col": year_col,
                "month_col": month_col,
            }

            if not product_col or product_col not in columns:
                return render_template(
                    "index.html",
                    error="Please enter a valid product column name.",
                    columns=columns,
                    file_token=file_token,
                    defaults=defaults,
                    selected_mode=time_mode,
                )

            if total_col and total_col in columns:
                df["total"] = pd.to_numeric(df[total_col], errors="coerce")
            elif quantity_col in columns and price_col in columns:
                df["total"] = pd.to_numeric(df[quantity_col], errors="coerce") * pd.to_numeric(
                    df[price_col], errors="coerce"
                )
            else:
                return render_template(
                    "index.html",
                    error="Enter total column name, or both quantity and price column names.",
                    columns=columns,
                    file_token=file_token,
                    defaults=defaults,
                    selected_mode=time_mode,
                )

            df["product"] = df[product_col]

            if quantity_col in columns:
                df["quantity"] = pd.to_numeric(df[quantity_col], errors="coerce")

            df.dropna(subset=["product", "total"], inplace=True)
            if df.empty:
                return render_template(
                    "index.html",
                    error="No valid rows after applying selected columns.",
                    columns=columns,
                    file_token=file_token,
                    defaults=defaults,
                    selected_mode=time_mode,
                )

            chart_df = df.copy()

            if time_mode == "date":
                if date_col not in columns:
                    return render_template(
                        "index.html",
                        error="Date mode requires a valid date column selection.",
                        columns=columns,
                        file_token=file_token,
                        defaults=defaults,
                        selected_mode=time_mode,
                    )
                chart_df["date"] = pd.to_datetime(chart_df[date_col], errors="coerce")
                chart_df.dropna(subset=["date"], inplace=True)
                grouped = chart_df.groupby(chart_df["date"].dt.to_period("M"))["total"].sum().sort_index()
                labels = grouped.index.astype(str).tolist()
                values = grouped.values.tolist()

            elif time_mode == "year_month":
                if year_col not in columns or month_col not in columns:
                    return render_template(
                        "index.html",
                        error="Year + Month mode requires both year and month column selections.",
                        columns=columns,
                        file_token=file_token,
                        defaults=defaults,
                        selected_mode=time_mode,
                    )
                chart_df["year_num"] = pd.to_numeric(chart_df[year_col], errors="coerce")
                chart_df["month_num"] = parse_month_to_number(chart_df[month_col])
                chart_df.dropna(subset=["year_num", "month_num"], inplace=True)
                chart_df = chart_df[(chart_df["month_num"] >= 1) & (chart_df["month_num"] <= 12)]
                chart_df["period"] = pd.PeriodIndex(
                    year=chart_df["year_num"].astype(int),
                    month=chart_df["month_num"].astype(int),
                    freq="M",
                )
                grouped = chart_df.groupby("period")["total"].sum().sort_index()
                labels = grouped.index.astype(str).tolist()
                values = grouped.values.tolist()

            elif time_mode == "year":
                if year_col not in columns:
                    return render_template(
                        "index.html",
                        error="Year mode requires a valid year column selection.",
                        columns=columns,
                        file_token=file_token,
                        defaults=defaults,
                        selected_mode=time_mode,
                    )
                chart_df["year_num"] = pd.to_numeric(chart_df[year_col], errors="coerce")
                chart_df.dropna(subset=["year_num"], inplace=True)
                grouped = chart_df.groupby(chart_df["year_num"].astype(int))["total"].sum().sort_index()
                labels = [str(int(year)) for year in grouped.index.tolist()]
                values = grouped.values.tolist()

            else:  # month
                if month_col not in columns:
                    return render_template(
                        "index.html",
                        error="Month mode requires a valid month column selection.",
                        columns=columns,
                        file_token=file_token,
                        defaults=defaults,
                        selected_mode=time_mode,
                    )
                chart_df["month_num"] = parse_month_to_number(chart_df[month_col])
                chart_df.dropna(subset=["month_num"], inplace=True)
                chart_df = chart_df[(chart_df["month_num"] >= 1) & (chart_df["month_num"] <= 12)]
                grouped = chart_df.groupby(chart_df["month_num"].astype(int))["total"].sum().sort_index()
                labels = [calendar.month_abbr[int(month)] for month in grouped.index.tolist()]
                values = grouped.values.tolist()

            if chart_df.empty or not labels:
                return render_template(
                    "index.html",
                    error="No valid time values found for selected columns.",
                    columns=columns,
                    file_token=file_token,
                    defaults=defaults,
                    selected_mode=time_mode,
                )

            total_revenue = df["total"].sum()
            if "quantity" in df.columns and df["quantity"].notna().any():
                best_product = df.groupby("product")["quantity"].sum().idxmax()
            else:
                best_product = df.groupby("product")["total"].sum().idxmax()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"sales_report_{timestamp}.xlsx"
            pdf_filename = f"summary_{timestamp}.pdf"
            excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
            pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)

            df.to_excel(excel_path, index=False)

            doc = SimpleDocTemplate(pdf_path)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph(f"Total Revenue: ₹{total_revenue}", styles["Normal"]))
            elements.append(Paragraph(f"Best Product: {best_product}", styles["Normal"]))
            doc.build(elements)

            shutil.copyfile(excel_path, os.path.join(OUTPUT_FOLDER, "sales_report.xlsx"))
            shutil.copyfile(pdf_path, os.path.join(OUTPUT_FOLDER, "summary.pdf"))

            # Save chart data to history for later review
            save_chart_to_history(labels, values, total_revenue, best_product, time_mode, excel_filename)

            return render_template(
                "index.html",
                revenue=total_revenue,
                product=best_product,
                labels=labels,
                values=values,
                used_basis=time_mode,
                columns=columns,
                file_token=file_token,
                defaults=defaults,
                selected_mode=time_mode,
            )

    # Handle loading chart from history
    loaded_chart_id = request.args.get("loaded_chart", "").strip()
    if loaded_chart_id:
        history = load_chart_history()
        for entry in history:
            if entry.get("id") == loaded_chart_id:
                return render_template(
                    "index.html",
                    revenue=entry.get("revenue"),
                    product=entry.get("product"),
                    labels=entry.get("labels"),
                    values=entry.get("values"),
                    used_basis=entry.get("time_mode"),
                    selected_mode=entry.get("time_mode", "date"),
                    loaded_from_history=True,
                )

    return render_template("index.html", selected_mode="date")


@app.route("/reports")
def reports_page():
    reports = list_reports()
    return render_template("reports.html", reports=reports)


@app.route("/analytics")
def analytics_page():
    summary = build_analytics_summary()
    return render_template("analytics.html", **summary)


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        upload_folder_input = request.form.get("upload_folder", "")
        output_folder_input = request.form.get("output_folder", "")

        upload_folder = normalize_storage_path(upload_folder_input, "uploads")
        output_folder = normalize_storage_path(output_folder_input, "output")

        try:
            apply_storage_paths(upload_folder, output_folder)
            save_storage_config(upload_folder, output_folder)
            success_message = "Storage paths updated successfully."
            summary = build_settings_summary()
            return render_template("settings.html", success=success_message, **summary)
        except Exception:
            summary = build_settings_summary()
            error_message = "Unable to update storage paths. Please verify folder paths and permissions."
            return render_template("settings.html", error=error_message, **summary)

    summary = build_settings_summary()
    return render_template("settings.html", **summary)


@app.route("/admin")
def admin_page():
    admin_info = build_admin_summary()
    return render_template("admin.html", **admin_info)


@app.route("/api/list_dirs")
def api_list_dirs():
    path = request.args.get("path", "").strip()

    if not path:
        return jsonify({"current": "", "parent": None, "directories": get_directory_roots()})

    normalized = os.path.abspath(path)
    if not os.path.isdir(normalized):
        return jsonify({"error": "Directory not found."}), 404

    parent = os.path.dirname(normalized)
    if parent == normalized:
        parent = None

    directories = []
    try:
        for name in os.listdir(normalized):
            full_path = os.path.join(normalized, name)
            if os.path.isdir(full_path):
                directories.append(full_path)
    except PermissionError:
        return jsonify({"error": "Permission denied for this directory."}), 403

    directories.sort(key=lambda item: item.lower())
    return jsonify({"current": normalized, "parent": parent, "directories": directories})


@app.route("/api/quick_path")
def api_quick_path():
    path_type = request.args.get("type", "").strip()
    if not path_type:
        return jsonify({"error": "Path type is required."}), 400
    
    quick_path = get_quick_access_path(path_type)
    if quick_path:
        return jsonify({"path": quick_path})
    return jsonify({"error": f"Path '{path_type}' not available."}), 404


@app.route("/api/chart_history")
def api_chart_history():
    history = load_chart_history()
    # Return summary list without full data
    summary = []
    for entry in history:
        summary.append({
            "id": entry.get("id"),
            "timestamp": entry.get("timestamp"),
            "revenue": entry.get("revenue"),
            "product": entry.get("product"),
            "time_mode": entry.get("time_mode"),
            "filename": entry.get("filename", ""),
        })
    return jsonify(summary)


@app.route("/api/chart_history/<chart_id>")
def api_chart_history_detail(chart_id):
    history = load_chart_history()
    for entry in history:
        if entry.get("id") == chart_id:
            return jsonify(entry)
    return jsonify({"error": "Chart not found"}), 404


@app.route("/download_report/<path:filename>")
def download_report(filename):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_FOLDER, safe_name)

    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(OUTPUT_FOLDER, safe_name, as_attachment=True)


@app.route("/download_excel")
def download_excel():
    return send_file(os.path.join(OUTPUT_FOLDER, "sales_report.xlsx"), as_attachment=True)


@app.route("/download_pdf")
def download_pdf():
    return send_file(os.path.join(OUTPUT_FOLDER, "summary.pdf"), as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)