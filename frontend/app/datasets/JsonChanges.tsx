import type { JsonChange } from "../datasetApi";

const display = (exists: boolean, value: unknown) => !exists ? "(không có trường này)"
  : typeof value === "string" ? value : JSON.stringify(value, null, 2);
export default function JsonChanges({changes, left = "Local", right = "Bản nhập"}: {
  changes: JsonChange[]; left?: string; right?: string;
}) {
  return <details><summary>{changes.length} trường khác biệt · xem đối chiếu</summary>
    {changes.map((change) => <article key={change.path} className="output-change">
      <h3>{change.path}</h3><div className="output-compare-selectors">
        <div><strong>{left}</strong><pre className="dataset-json">{display(change.before_exists, change.before)}</pre></div>
        <div><strong>{right}</strong><pre className="dataset-json">{display(change.after_exists, change.after)}</pre></div>
      </div>
    </article>)}
  </details>;
}
