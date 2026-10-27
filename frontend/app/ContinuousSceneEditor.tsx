"use client";

import {useEffect, useId, useRef, useState, type KeyboardEvent} from 'react';
import type {ScriptBlock, ScriptScene} from './screenplayTypes';
import {checkScriptSceneEdit, mergeScriptBlock, splitScriptBlock} from './screenplayEditing';

type Part = 'action' | 'character' | 'dialogue';
type Focus = {id: string; field: 'text' | 'speaker'; position?: number};

export function ContinuousSceneEditor({scene, scope, blockLimit, onChange}: {
  scene: ScriptScene; scope: string; blockLimit: number; onChange: (scene: ScriptScene) => void;
}) {
  const prefix = useId(), host = useRef<HTMLDivElement>(null);
  const [placeholderId, setPlaceholderId] = useState(() => crypto.randomUUID());
  const [active, setActive] = useState<{id: string; part: Part}>({id: scene.blocks[0]?.id ?? placeholderId, part: 'action'});
  const [focus, setFocus] = useState<Focus | null>(null), [error, setError] = useState('');
  const [undo, setUndo] = useState<{before: ScriptScene; after: string; scope: string} | null>(null);
  const blocks: ScriptBlock[] = scene.blocks.length ? scene.blocks : [{id: placeholderId, kind: 'action', text: '', speaker: ''}];
  const block = blocks.find(b => b.id === active.id) ?? blocks[0];
  const part = block.kind === 'action' ? 'action' : active.id === block.id && active.part === 'character' ? 'character' : 'dialogue';
  const current = {...scene, blocks};

  useEffect(() => {
    if (!focus) return;
    const node = host.current?.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[data-script-block="${focus.id}"] [data-script-field="${focus.field}"]`);
    if (node) {node.focus(); const pos = Math.min(focus.position ?? node.value.length, node.value.length); node.setSelectionRange(pos, pos);}
    setFocus(null);
  }, [focus]);

  function change(next: ScriptScene, destination?: Focus, remember = false) {
    try {checkScriptSceneEdit(next, blockLimit);} catch (caught) {setError((caught as Error).message); return;}
    if (remember) setUndo({before: structuredClone(scene), after: JSON.stringify(next), scope});
    if (!scene.blocks.length && next.blocks.some(b => b.id === placeholderId)) setPlaceholderId(crypto.randomUUID());
    setError(''); onChange(next);
    if (destination) setFocus(destination);
  }
  function edit(id: string, field: 'text' | 'speaker', value: string) {
    if (!scene.blocks.length && !value) return;
    change({...current, blocks: blocks.map(b => b.id === id ? {...b, [field]: value} : b)});
  }
  function convert(next: Part) {
    if (next === 'action' && block.kind === 'dialogue' && block.speaker &&
        !window.confirm(`Đổi sang hành động sẽ bỏ tên người nói “${block.speaker}”; giữ nguyên nội dung. Có thể hoàn tác ngay. Tiếp tục?`)) return;
    const kind = next === 'action' ? 'action' : 'dialogue';
    setActive({id: block.id, part: next});
    const destination: Focus = {id: block.id, field: next === 'character' ? 'speaker' : 'text'};
    if (kind === block.kind) {setFocus(destination); return;}
    change({...current, blocks: blocks.map(b => b.id === block.id ? {...b, kind, speaker: ''} : b)}, destination, true);
  }
  function join(id: string) {
    try {
      const index = scene.blocks.findIndex(b => b.id === id), previous = scene.blocks[index - 1];
      change(mergeScriptBlock(scene, id), {id: previous.id, field: 'text', position: previous.text.replace(/\r\n/g, '\n').length}, true);
    } catch (caught) {setError((caught as Error).message);}
  }
  function key(event: KeyboardEvent<HTMLTextAreaElement>, b: ScriptBlock) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    const {selectionStart: start, selectionEnd: end} = event.currentTarget;
    if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault(); const id = crypto.randomUUID();
      change(splitScriptBlock(current, b.id, start, end, id), {id, field: 'text', position: 0}, true);
    } else if (event.key === 'Backspace' && !event.ctrlKey && !event.metaKey && !event.altKey && start === 0 && end === 0 && blocks[0].id !== b.id) {
      event.preventDefault(); join(b.id);
    }
  }
  function move(id: string, by: number) {
    const next = [...scene.blocks], index = next.findIndex(b => b.id === id);
    [next[index], next[index + by]] = [next[index + by], next[index]];
    change({...scene, blocks: next}, {id, field: 'text'}, true);
  }
  function remove(index: number) {
    const next = scene.blocks.filter((_, i) => i !== index);
    change({...scene, blocks: next}, {id: next[index]?.id ?? next[index - 1]?.id ?? placeholderId, field: 'text'}, true);
  }

  return <div ref={host} className="screenplay-scene continuous-scene" aria-label="Editor liền mạch thử nghiệm">
    <label>Tiêu đề cảnh<input maxLength={500} value={scene.heading} onChange={e => change({...scene, heading: e.target.value})}/></label>
    <div className="continuous-toolbar">
      <label htmlFor={`${prefix}-format`}>Đang viết</label>
      <select id={`${prefix}-format`} value={part} onChange={e => convert(e.target.value as Part)}>
        <option value="action">Hành động</option><option value="character">Nhân vật</option><option value="dialogue">Lời thoại</option>
      </select>
      <details><summary>Cách viết</summary><p>Enter sang đoạn hành động tiếp. Chọn Nhân vật, gõ tên rồi Enter để viết lời thoại. Shift+Enter xuống dòng trong cùng đoạn. Tab chuyển focus. Dán văn bản giữ các xuống dòng trong đoạn, không tự đoán người nói.</p></details>
    </div>
    {error && <p role="alert">{error}</p>}
    <div className="continuous-page">
      {blocks.map((b, index) => <div key={b.id} className={`continuous-block continuous-${b.kind}`} data-script-block={b.id}>
        {b.kind === 'dialogue' && <>
          <label className="sr-only" htmlFor={`${prefix}-${b.id}-speaker`}>Người nói đoạn {index + 1}</label>
          <input id={`${prefix}-${b.id}-speaker`} data-script-field="speaker" maxLength={200} placeholder="Tên nhân vật" value={b.speaker}
            onFocus={() => setActive({id: b.id, part: 'character'})} onChange={e => edit(b.id, 'speaker', e.target.value)}
            onKeyDown={e => {if (e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229) {e.preventDefault(); setActive({id: b.id, part: 'dialogue'}); setFocus({id: b.id, field: 'text', position: 0});}}}/>
        </>}
        <label className="sr-only" htmlFor={`${prefix}-${b.id}-text`}>{b.kind === 'action' ? 'Hành động' : 'Lời thoại'} đoạn {index + 1}</label>
        <textarea id={`${prefix}-${b.id}-text`} data-script-field="text" rows={3} maxLength={10000} value={b.text}
          placeholder={b.kind === 'action' ? 'Viết điều người xem nhìn hoặc nghe thấy…' : 'Nhân vật nói gì?'}
          onFocus={() => setActive({id: b.id, part: b.kind})} onChange={e => edit(b.id, 'text', e.target.value)} onKeyDown={e => key(e, b)}/>
        {scene.blocks.length > 0 && <details className="continuous-block-menu"><summary>Thao tác đoạn {index + 1}</summary>
          <button type="button" disabled={index === 0} onClick={() => move(b.id, -1)}>Đưa khối lên</button>
          <button type="button" disabled={index === blocks.length - 1} onClick={() => move(b.id, 1)}>Đưa khối xuống</button>
          <button type="button" disabled={index === 0} onClick={() => join(b.id)}>Gộp với đoạn trước</button>
          <button type="button" onClick={() => remove(index)}>Xóa khối</button>
        </details>}
      </div>)}
    </div>
    {undo && undo.scope === scope && JSON.stringify(scene) === undo.after && <button type="button" onClick={() => {
      onChange(undo.before); setUndo(null); setError('');
    }}>Hoàn tác thao tác đoạn</button>}
    <p className="storage-note">Đang thử editor cho cảnh này; lưu và bản nguồn vẫn dùng luồng hiện có. Không cần thêm thoại để lưu nháp.</p>
  </div>;
}
