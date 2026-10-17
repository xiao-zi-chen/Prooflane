function strategySelection() {
 const kind=state.strategyKind || 'macos';
 const candidates=strategyCandidates(kind);
 state.strategySelections ??= {};
 const selected=state.strategySelections[kind];
 return candidates.find(run=>run.id===selected) || null;
}
function strategyCandidates(kind) {
 const runs=state.runs.filter(run=>run.platform===kind),extra=state.strategyExternalRun;
 return extra?.platform===kind&&!runs.some(run=>run.id===extra.id)?[extra,...runs]:runs;
}
function strategyKitUrl() {
 const kind=state.strategyKind || 'macos',run=strategySelection(),params=new URLSearchParams();
 if(run)params.set('run_id',run.id);
 if(run && $('#strategy-include')?.checked)params.set('include_package','true');
 return `/api/strategies/${kind}/kit?${params}`;
}
async function renderStrategy() {
 if(!state.strategies)state.strategies=await api('/api/strategies');
 if(state.route!=='strategy')return;
 const kind=state.strategyKind || 'macos',plan=state.strategies.find(item=>item.id===kind),selected=state.strategySelections?.[kind];
 if(selected&&!strategySelection()) {
  const external=await api(`/api/runs/${selected}`);
  if(state.route!=='strategy'||state.strategyKind!==kind||state.strategySelections?.[kind]!==selected)return;
  if(external.platform!==kind)throw new Error('所选任务不属于此平台');
  state.strategyExternalRun=external;
 }
 const run=strategySelection(),candidates=strategyCandidates(kind);
 const stamp=JSON.stringify([kind,run?.id,candidates.map(item=>[item.id,item.name,item.package.name]),state.strategyWithPackage]);
 if(stamp===state.strategyStamp)return;
 state.strategyStamp=stamp;
 $('#strategy-content').innerHTML=`
 <nav class="strategy-platforms" aria-label="选择执行平台">
  ${state.strategies.map(item=>`<a href="#strategy/${item.id}" class="${kind===item.id?'selected':''}" aria-current="${kind===item.id?'page':'false'}">${osMark(item.id)}<span>${esc(item.name)}</span></a>`).join('')}
 </nav>
 <div class="strategy-grid">
  <section class="strategy-delivery" aria-labelledby="strategy-export-title">
   <h2 id="strategy-export-title">导出 ${esc(plan.name)} 执行包</h2>
   <label for="strategy-run">测试任务</label>
   <select id="strategy-run" aria-describedby="strategy-binding">
    <option value="" ${!run?'selected':''}>通用策略（未绑定任务）</option>
    ${candidates.map(item=>`<option value="${item.id}" ${item.id===run?.id?'selected':''}>${esc(item.name)} · ${item.id.slice(0,8)}</option>`).join('')}
   </select>
   <p id="strategy-binding">${run?'已包含验收步骤和运行工具，可在测试者的电脑上独立执行。':'只包含说明和模板。选择具体任务后，包内会附带验收步骤和运行工具。'}</p>
   ${run?`<dl class="strategy-task"><div><dt>应用文件</dt><dd>${esc(run.package.name)}</dd></div><div><dt>目标架构</dt><dd>${esc(run.architecture)}<span> · ${run.steps.length} 步验收</span></dd></div></dl>
   <details class="strategy-hash"><summary>构建校验信息</summary><code>SHA-256<br>${esc(run.package.sha256)}</code><a href="#run/${run.id}">查看原任务 →</a></details>`:''}
   <label class="strategy-checkbox" ${!run?'hidden':''}><input type="checkbox" id="strategy-include" ${!run?'disabled':''} ${run&&state.strategyWithPackage?'checked':''}>将应用文件一起放入 ZIP</label>
   ${run?'<p class="field-help">未勾选时，需另外发送同一份应用文件。</p>':''}
   <div class="strategy-actions"><a class="button primary" id="strategy-download" download>${icon('download')}${run?'下载执行包':'下载说明包'}</a><button class="button secondary" id="strategy-copy">${icon('copy')}复制邀请文字</button></div>
   <p class="strategy-review">${run?'测试者运行后返回 receipt.json 和 evidence.zip。结果需人工复核，不会自动写回控制台。':'先把说明包发给测试者，确认设备和时间后，再选择具体任务导出执行包。'}</p>
   <div class="strategy-details">
    <details><summary>包内文件</summary><p>环境要求、操作说明、验收表和问题记录模板。${run?'另含此任务的场景配置与独立运行工具。':'未包含应用文件和运行工具。'}</p></details>
    <details><summary>执行与回传</summary><ol>
     <li>确认系统和架构，按 README 安装依赖，运行 <code>--check</code> 检查环境。</li>
     <li>运行验收步骤。需要复测时先重置环境，每次结果单独保留。</li>
     <li>返回证据 ZIP、回执和问题记录。复核者核对构建、步骤及截图，再登记结论。</li>
    </ol><p>遇到阻塞时，返回错误提示与环境信息；应用问题修复后使用新构建复测。</p></details>
   </div>
  </section>
  <aside class="strategy-reference" aria-label="平台要求">
   <section><h2>联系测试者</h2><p>${esc(plan.audience)}。</p><p>确认系统、架构、可执行时间和费用，由对方安排设备。</p></section>
   <section><h2>环境要求</h2><p>${esc(plan.environment)}</p><p class="strategy-formats">应用格式：${esc(plan.formats)}</p></section>
   <section><h2>验证情况</h2><p>${esc(plan.validation)}</p></section>
   <details class="strategy-blockers"><summary>常见问题</summary><ul>${plan.pitfalls.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details>
   <a class="strategy-node-link" href="#nodes/${kind}">需要持续测试？接入 ${esc(plan.name)} 节点 →</a>
  </aside>
 </div>`;
 $('#strategy-download').href=strategyKitUrl();
 $('#strategy-run').addEventListener('change',event=>{state.strategySelections[kind]=event.target.value;state.strategyWithPackage=false;renderStrategy().catch(error=>toast(error.message,true));});
 $('#strategy-include').addEventListener('change',event=>{
  state.strategyWithPackage=event.target.checked;
  $('#strategy-download').href=strategyKitUrl();
  // Keep the polling fingerprint in sync so a checkbox change does not close details or steal focus.
  state.strategyStamp=JSON.stringify([kind,run?.id,candidates.map(item=>[item.id,item.name,item.package.name]),state.strategyWithPackage]);
 });
 $('#strategy-copy').addEventListener('click',async event=>{
  const button=event.currentTarget;button.disabled=true;
  try {
   const selected=strategySelection(),query=selected?`?run_id=${selected.id}`:'';
   const reply=await api(`/api/strategies/${kind}/invitation${query}`);
   await navigator.clipboard.writeText(reply.text);
   toast('邀请文字已复制');
  } catch(error) {toast(error.message,true);}
  finally {button.disabled=false;}
 });
}