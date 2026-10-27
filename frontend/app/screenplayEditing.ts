import type {ScriptScene} from './screenplayTypes';

// Positions are native input offsets (UTF-16); text is never normalized or reparsed.
export function splitScriptBlock(scene: ScriptScene, id: string, start: number, end: number, newId: string): ScriptScene {
  const index = scene.blocks.findIndex(b => b.id === id), block = scene.blocks[index];
  if (!block || start < 0 || end < start || end > block.text.length || scene.blocks.some(b => b.id === newId)) {
    throw new Error('Không xác định được đoạn cần tách. Bản đang viết vẫn giữ.');
  }
  return {...scene, blocks: [
    ...scene.blocks.slice(0, index), {...block, text: block.text.slice(0, start)},
    {id: newId, kind: 'action', speaker: '', text: block.text.slice(end)}, ...scene.blocks.slice(index + 1),
  ]};
}

export function mergeScriptBlock(scene: ScriptScene, id: string): ScriptScene {
  const index = scene.blocks.findIndex(b => b.id === id), block = scene.blocks[index], previous = scene.blocks[index - 1];
  if (!previous || !block || previous.kind !== block.kind || previous.speaker !== block.speaker) {
    throw new Error('Chỉ gộp hai đoạn cùng loại và cùng người nói; nội dung vẫn giữ nguyên.');
  }
  return {...scene, blocks: [
    ...scene.blocks.slice(0, index - 1), {...previous, text: previous.text + block.text}, ...scene.blocks.slice(index + 1),
  ]};
}

export function checkScriptSceneEdit(scene: ScriptScene, blockLimit = 200): void {
  if (scene.blocks.length > blockLimit) throw new Error('Đã tới giới hạn số khối; hãy sửa đoạn đang có.');
  if (scene.blocks.some(b => [...b.text].length > 10000 || [...b.speaker].length > 200)) {
    throw new Error('Đoạn vượt giới hạn nội dung hoặc tên người nói; bản trước vẫn giữ nguyên.');
  }
}
