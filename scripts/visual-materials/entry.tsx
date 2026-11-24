import React from 'react';
import {createRoot} from 'react-dom/client';
import {ExportView} from '@overlay/ExportView';
import {EFFECTS} from '@overlay/effects/registry';
import {createScene} from '@table/scene.cjs';

const job = window.__MATERIAL_JOB;
window.__MATERIAL_CARDS = EFFECTS.map(({id, name, description, defaults, tags}) => ({id, name, description, defaults, tags}));
if (job.engine === 'overlay') {
  const ids = new Set(EFFECTS.map(e => e.id));
  for (const card of job.input.cards) {
    if (!ids.has(card.kind)) throw Error('Unknown overlay kind: ' + card.kind);
    const effect = EFFECTS.find(e => e.id === card.kind)!;
    card.params = {...effect.defaults, ...card.params};
  }
  window.__EXPORT_DOC = JSON.stringify(job.input);
  createRoot(document.getElementById('root')!).render(<ExportView />);
} else {
  const scene = createScene(job.input);
  window.__materialFrame = (t: number) => {
    const result = scene.render(t);
    document.getElementById('root')!.innerHTML = result.html;
    return {semantic: result.semantic, state: result.state};
  };
}
