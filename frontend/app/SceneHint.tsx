"use client";

import {useId, useState, type ReactNode} from "react";

export function SceneHint({title, children, heading = "h4", titleId}: {
  title: string; children: ReactNode; heading?: "h3" | "h4"; titleId?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId(), Heading = heading;
  return <div className="scene-help"><div className="scene-help-heading"><Heading id={titleId}>{title}</Heading>
    <button type="button" className="scene-info" aria-label={`Thông tin: ${title}`} aria-expanded={open} aria-controls={id}
      onClick={() => setOpen(!open)}>ⓘ</button></div>
    <div className={`scene-help-content${open ? " is-open" : ""}`} id={id} aria-hidden={!open} inert={!open}>
      <div><div className="storage-note">{children}</div></div>
    </div>
  </div>;
}
