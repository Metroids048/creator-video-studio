import fs from 'node:fs/promises';
import { analyzeCommerceRouting, commerceRoutePolicyV2 } from '../sources/hyperframe-local/video-agent/lib/orchestration/commerce-router-v2.mjs';

const task = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
if (task.scenario && !commerceRoutePolicyV2.scenarios.some(s => s.id === task.scenario)) {
  throw Error('商务场景 ID 不在原生路由合同中');
}
const result = analyzeCommerceRouting(task.request, {
  selectedScenarioId: task.scenario,
  currentRevisionId: task.version,
});
console.log(JSON.stringify(result));
