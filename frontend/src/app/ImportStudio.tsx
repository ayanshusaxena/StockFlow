import {
  ArrowRight,
  BadgeCheck,
  Check,
  CheckCircle2,
  FileCheck2,
  FileSpreadsheet,
  Upload,
  X,
  XCircle,
} from "lucide-react";
import { Link } from "react-router";
import { useRef, useState, type DragEvent } from "react";
import type { ImportPreview, ImportResult } from "./api";
import { useAppStore } from "./store";

const steps = ["Upload", "Validate & Clean", "Review", "Results"];

export default function ImportStudio() {
  const { previewImport, commitImport } = useAppStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const importKeyRef = useRef(crypto.randomUUID());
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [stage, setStage] = useState(1);
  const [review, setReview] = useState<"valid" | "rejected">("valid");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selectFile = (selected?: File) => {
    if (!selected) return;
    setFile(selected);
    setPreview(null);
    setResult(null);
    setStage(1);
    setError("");
    importKeyRef.current = crypto.randomUUID();
  };
  const validate = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError("");
    try {
      setPreview(await previewImport(file));
      setStage(2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CSV could not be validated.");
    } finally {
      setBusy(false);
    }
  };
  const commit = async () => {
    if (!file || !preview?.can_commit || busy) return;
    setBusy(true);
    setError("");
    try {
      setResult(await commitImport(file, importKeyRef.current));
      setStage(4);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CSV import failed.");
    } finally {
      setBusy(false);
    }
  };
  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError("");
    setReview("valid");
    setStage(1);
    importKeyRef.current = crypto.randomUUID();
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="breadcrumb"><span>StockFlow</span><ArrowRight size={12} /><span>Data Import Studio</span></div>
          <h1>Data Import Studio</h1>
          <p>Validate, clean and review CSV inventory data before committing it to the database.</p>
        </div>
      </div>
      <div className="import-steps">
        {steps.map((label, index) => {
          const number = index + 1;
          return (
            <button
              key={label}
              disabled={number > stage}
              className={number === stage ? "active" : number < stage ? "done" : ""}
              aria-current={number === stage ? "step" : undefined}
              onClick={() => number < stage && setStage(number)}
            >
              <i>{number < stage ? <Check size={14} /> : number}</i>
              <span><small>Stage {number}</small><strong>{label}</strong></span>
            </button>
          );
        })}
      </div>
      {error && <div className="api-error-banner" role="alert"><XCircle size={18} /><span>{error}</span></div>}
      <section className="import-surface">
        {stage === 1 && (
          <div className="upload-layout">
            <div
              className={file ? "drop-zone selected" : "drop-zone"}
              onDragOver={(event) => event.preventDefault()}
              onDrop={onDrop}
            >
              <input
                ref={inputRef}
                hidden
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => selectFile(event.target.files?.[0])}
              />
              <span className="upload-symbol"><Upload size={25} /></span>
              <h2>{file ? "CSV ready to validate" : "Drop your inventory CSV here"}</h2>
              <p>{file ? "The backend will validate references and values before any write." : "Choose a CSV from your device."}</p>
              {file ? (
                <div className="selected-file">
                  <FileSpreadsheet size={21} />
                  <span><strong>{file.name}</strong><small>{Math.max(1, Math.round(file.size / 1024))} KB · CSV file</small></span>
                  <button onClick={() => {
                    setFile(null);
                    setPreview(null);
                    setResult(null);
                    setError("");
                    setStage(1);
                    importKeyRef.current = crypto.randomUUID();
                  }} aria-label="Remove file"><X size={17} /></button>
                </div>
              ) : (
                <button className="button secondary" onClick={() => inputRef.current?.click()}>Choose CSV file</button>
              )}
            </div>
            <aside className="expected-columns">
              <span className="eyebrow">CSV STRUCTURE</span>
              <h3>Expected columns</h3>
              <p>One current stock snapshot per SKU and store.</p>
              {["SKU", "Store or Store Code", "Quantity", "Reorder Level (optional)"].map((column, index) => (
                <div key={column}><b>{String(index + 1).padStart(2, "0")}</b><span>{column}</span><small>{index === 2 || index === 3 ? "Whole number" : "Known value"}</small></div>
              ))}
              <p className="notice"><FileCheck2 size={16} /> All-or-nothing: any rejected row blocks the entire commit.</p>
            </aside>
            <div className="import-action">
              <span>{file ? `${file.name} is ready.` : "Select a CSV to continue."}</span>
              <button className="button primary" disabled={!file || busy} onClick={() => void validate()}>
                {busy ? "Validating…" : "Validate & clean"} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
        {stage === 2 && preview && file && (
          <ValidationStage file={file} preview={preview} onBack={() => setStage(1)} onContinue={() => setStage(3)} />
        )}
        {stage === 3 && preview && (
          <ReviewStage preview={preview} review={review} setReview={setReview} onBack={() => setStage(2)} onImport={() => void commit()} busy={busy} />
        )}
        {stage === 4 && result && <ResultsStage result={result} onReset={reset} />}
      </section>
    </>
  );
}

function FileBanner({ file, rows }: { file: File; rows: number }) {
  return <div className="file-banner"><span><FileSpreadsheet size={20} /><span><strong>{file.name}</strong><small>{rows} data rows detected</small></span></span><span className="verified"><BadgeCheck size={16} /> CSV parsed by backend</span></div>;
}

function ValidationStage({ file, preview, onBack, onContinue }: { file: File; preview: ImportPreview; onBack: () => void; onContinue: () => void }) {
  return <>
    <FileBanner file={file} rows={preview.total_rows} />
    <div className="validation-content">
      <div className="validation-stats">
        <div><span>Total rows</span><strong>{preview.total_rows}</strong></div>
        <div className="healthy"><span>Accepted rows</span><strong>{preview.accepted_count}</strong></div>
        <div className="critical"><span>Rejected rows</span><strong>{preview.rejected_count}</strong></div>
      </div>
      <div className="section-heading"><div><span className="section-index">02</span><h2>Backend validation results</h2></div><p>Values are trimmed and references resolved against active database records.</p></div>
      <div className="comparison-list">
        {preview.accepted_rows.map((row) => <article className="comparison-row" key={`${row.row_number}-${row.sku}-${row.store_code}`}>
          <div className="row-number">{String(row.row_number).padStart(2, "0")}</div>
          <div><span>Source row</span><code>{row.sku} · {row.store_code} · {row.new_quantity}</code></div><ArrowRight size={17} />
          <div><span>Resolved record</span><code>{row.product_name} · {row.store_name} · {row.new_quantity}</code></div>
          <p><CheckCircle2 size={15} /> Accepted · current stock {row.old_quantity}</p>
        </article>)}
        {preview.rejected_rows.map((row) => <article className="comparison-row rejected" key={`rejected-${row.row_number}`}>
          <div className="row-number">{String(row.row_number).padStart(2, "0")}</div>
          <div><span>Source row</span><code>{Object.values(row.values).join(" · ") || "∅"}</code></div><ArrowRight size={17} />
          <div><span>Validation</span><code>{row.errors.join("; ")}</code></div>
          <p><XCircle size={15} /> Rejected · no changes applied</p>
        </article>)}
      </div>
    </div>
    <div className="import-footer"><button className="button secondary" onClick={onBack}>Back</button><span>Review every rejected row before commit.</span><button className="button primary" onClick={onContinue}>Review results <ArrowRight size={16} /></button></div>
  </>;
}

function ReviewStage({ preview, review, setReview, onBack, onImport, busy }: { preview: ImportPreview; review: "valid" | "rejected"; setReview: (value: "valid" | "rejected") => void; onBack: () => void; onImport: () => void; busy: boolean }) {
  const rows = review === "valid" ? preview.accepted_rows : preview.rejected_rows;
  return <>
    <div className="review-head"><div><span className="eyebrow">STAGE 3 · REVIEW</span><h2>Confirm what will—and will not—be imported</h2><p>Import policy: all-or-nothing. Rejected rows prevent every balance update.</p></div><div className="review-summary"><span><CheckCircle2 size={18} /><b>{preview.accepted_count}</b> accepted</span><span><XCircle size={18} /><b>{preview.rejected_count}</b> rejected</span></div></div>
    <div className="review-tabs" role="tablist" aria-label="Import record status">
      <button role="tab" aria-selected={review === "valid"} className={review === "valid" ? "active" : ""} onClick={() => setReview("valid")}>Accepted rows <b>{preview.accepted_count}</b></button>
      <button role="tab" aria-selected={review === "rejected"} className={review === "rejected" ? "active" : ""} onClick={() => setReview("rejected")}>Rejected rows <b>{preview.rejected_count}</b></button>
    </div>
    <div className="review-records">
      {review === "valid" && preview.accepted_rows.map((row) => <article key={`accepted-${row.row_number}`}><span className="review-state valid"><Check size={16} /></span><div><strong>{row.product_name}</strong><span>{row.sku} · {row.store_name} · {row.old_quantity} → {row.new_quantity}</span></div><p>Reorder level {row.reorder_level}</p></article>)}
      {review === "rejected" && preview.rejected_rows.map((row) => <article key={`reject-${row.row_number}`}><span className="review-state rejected"><X size={16} /></span><div><strong>Row {row.row_number}</strong><span>{Object.values(row.values).join(" · ")}</span></div><p>{row.errors.join("; ")}</p></article>)}
      {!rows.length && <p className="muted">No {review === "valid" ? "accepted" : "rejected"} rows.</p>}
    </div>
    <div className="import-summary"><div><FileCheck2 size={20} /><span><strong>Import summary</strong><small>{preview.can_commit ? `${preview.accepted_count} balance rows will be updated in one transaction.` : "The batch cannot be committed until every rejected row is corrected."}</small></span></div><span>{preview.rejected_count ? "No partial import will occur." : "No rejected rows."}</span></div>
    <div className="import-footer"><button className="button secondary" onClick={onBack}>Back</button><span>Database changes happen only after confirmation.</span><button className="button primary" disabled={!preview.can_commit || busy} onClick={onImport}>{busy ? "Importing…" : `Import ${preview.accepted_count} rows`}</button></div>
  </>;
}

function ResultsStage({ result, onReset }: { result: ImportResult; onReset: () => void }) {
  return <div className="results-stage">
    <span className="result-mark"><Check size={32} /></span><span className="eyebrow">IMPORT COMPLETE</span>
    <h2>{result.imported_count} rows imported successfully</h2>
    <p>{result.file_name} updated inventory in one database transaction. {result.changed_units} units changed and {result.history_entries} batch history entries were recorded.</p>
    <div className="result-cards"><div><CheckCircle2 size={20} /><span><strong>{result.imported_count}</strong><small>Imported rows</small></span></div><div className="rejected"><XCircle size={20} /><span><strong>{result.rejected_count}</strong><small>Rejected rows</small></span></div><div><FileSpreadsheet size={20} /><span><strong>{result.changed_units}</strong><small>Units changed</small></span></div></div>
    <div className="result-actions"><Link className="button primary" to="/inventory">View affected inventory <ArrowRight size={16} /></Link><button className="button secondary" onClick={onReset}>Start another import</button></div>
  </div>;
}
