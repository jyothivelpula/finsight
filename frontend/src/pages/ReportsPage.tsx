import { useState, type FormEvent } from "react";
import { Download } from "lucide-react";
import api from "../api/client";
import { reportsApi } from "../api/finsight";
import { Button, PageHeader, Panel, Select } from "../components/ui";
import { currentYearMonth } from "../lib/format";
import type { ReportResponse } from "../types";

export default function ReportsPage() {
  const { year, month } = currentYearMonth();
  const [reportType, setReportType] = useState("monthly");
  const [format, setFormat] = useState("pdf");
  const [result, setResult] = useState<ReportResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await reportsApi.generate({
        report_type: reportType,
        year,
        month,
        format,
      });
      setResult(res);
    } catch {
      setError("Could not generate report. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    if (!result) return;
    const response = await api.get(result.download_path, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader title="Reports" subtitle="Export monthly, income, expense, budget, and health reports" />
      <Panel className="max-w-xl">
        <form onSubmit={onSubmit} className="space-y-4">
          <Select label="Report type" value={reportType} onChange={(e) => setReportType(e.target.value)}>
            <option value="monthly">Monthly Financial Report</option>
            <option value="income">Income Report</option>
            <option value="expense">Expense Report</option>
            <option value="budget">Budget Report</option>
            <option value="savings">Savings Report</option>
            <option value="health">Financial Health Report</option>
          </Select>
          <Select label="Format" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="pdf">PDF</option>
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="csv">CSV</option>
          </Select>
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Generating…" : "Generate Report"}
          </Button>
        </form>
        {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
        {result ? (
          <button
            type="button"
            onClick={download}
            className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-moss"
          >
            <Download className="h-4 w-4" /> Download {result.filename}
          </button>
        ) : null}
      </Panel>
    </div>
  );
}
