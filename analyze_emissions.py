"""
Emissions data analysis script.

Reads primary measurements (primary_data.csv) and provenance records
(data/provenance.csv), merges them on the ID column, and keeps only records
that passed QC (qc == "PASS") and were accepted (provenance_status == "ACCEPT").

For each valid record, the corrected intensity is computed as raw - bias.
The script then prints a JSON summary with:
  - valid_records: number of records after filtering
  - high_count: records with corrected intensity >= 50
  - maximum_id / maximum_corrected: the record with the highest corrected value
  - mean_corrected: average corrected intensity

Input checks: required columns, duplicate IDs, non-numeric values, empty results.
"""

import json
import pandas as pd

# قراءة ملفات البيانات الأساسية وملف التوثيق
# بنقرا كل الأعمدة كنص عشان المعرفات تفضل زي ما هي (مثلاً "007" ما تتحولش لـ 7)
main_df = pd.read_csv("primary_data.csv", dtype=str)
prov_df = pd.read_csv("data/provenance.csv", dtype=str)

# المعرف هو العمود الأول في الملف الأساسي
id_col = main_df.columns[0]

# تحقق إن العمود موجود في ملف التوثيق كمان
if id_col not in prov_df.columns:
    raise KeyError(f"ID column '{id_col}' not found in provenance.csv")

# تحقق إن مفيش أعمدة مشتركة تانية غير المعرف (تسبب _x و _y بعد الدمج)
overlap = (set(main_df.columns) & set(prov_df.columns)) - {id_col}
if overlap:
    raise ValueError(f"Columns exist in both files: {sorted(overlap)}")

# تنظيف المسافات الزايدة في المعرفات قبل المطابقة
main_df[id_col] = main_df[id_col].str.strip()
prov_df[id_col] = prov_df[id_col].str.strip()

# مطابقة السجلات: validate بيرمي خطأ لو في معرف مكرر في أي ملف
df = pd.merge(main_df, prov_df, on=id_col, how="inner", validate="one_to_one")

# 1. التصفية حسب شروط QC و Provenance (مع تجاهل المسافات وحالة الحروف)
qc_ok = df["qc"].str.strip().str.upper() == "PASS"
prov_ok = df["provenance_status"].str.strip().str.upper() == "ACCEPT"
df_valid = df[qc_ok & prov_ok].copy()

# 2. تحويل الأعمدة الرقمية بأمان، واستبعاد السجلات اللي قيمها مش أرقام
df_valid["raw"] = pd.to_numeric(df_valid["raw"], errors="coerce")
df_valid["bias"] = pd.to_numeric(df_valid["bias"], errors="coerce")
df_valid = df_valid.dropna(subset=["raw", "bias"])

# تأكد إن في سجلات صالحة قبل ما نكمل
if df_valid.empty:
    raise ValueError("No valid records after filtering")

# 3. حساب شدة الانبعاثات المصححة
df_valid["corrected"] = df_valid["raw"] - df_valid["bias"]

# 4. حساب المؤشرات المطلوبة
valid_records = int(len(df_valid))

# الشدة العالية: القيمة المصححة >= 50
high_count = int((df_valid["corrected"] >= 50.0).sum())

# إيجاد السجل صاحب أعلى قيمة مصححة (لو في تعادل بيرجع أول سجل)
max_row = df_valid.loc[df_valid["corrected"].idxmax()]
maximum_id = str(max_row[id_col])
maximum_corrected = round(float(max_row["corrected"]), 3)
mean_corrected = round(float(df_valid["corrected"].mean()), 3)

# 5. تجهيز الناتج بالصيغة المطلوبة
output = {
    "valid_records": valid_records,
    "high_count": high_count,
    "maximum_id": maximum_id,
    "maximum_corrected": maximum_corrected,
    "mean_corrected": mean_corrected,
}

print(json.dumps(output, indent=2))
