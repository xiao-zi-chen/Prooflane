/* Shared native evidence views. Every image comes from the selected run. */
function visualSignature(value) {
 return JSON.stringify(value,(key,item)=>['last_seen','lease_until','lease'].includes(key)?undefined:item);
}
function osMark(kind) {
 const shapes={windows:'<path d="M3 4l8-1v8H3zm10-1 8-1v9h-8zM3 13h8v8l-8-1zm10 0h8v9l-8-1z"/>',macos:'<rect x="3" y="3" width="18" height="14" rx="3"/><path d="M8 21h8m-4-4v4M7 8h.01M17 8h.01M8 12q4 3 8 0"/>',linux:'<path d="m7 5 5-3 5 3 3 14-8 3-8-3zM9 8h.01M15 8h.01m-6 4 3 2 3-2M7 19l3-2m4 0 3 2"/>'};
 return `<span class="os-mark ${kind}"><svg viewBox="0 0 24 24" aria-hidden="true">${shapes[kind]}</svg></span>`;
}
function evidenceCard(kind,run,index,mode='image') {
 const platform=state.platforms.find(p=>p.id===kind),step=run?.steps[index];
 const node=(run?.worker_name || (platform?.available?'节点就绪':'无在线节点'))+(run?.architecture && run.architecture!=='any'?` · ${run.architecture}`:'');
 let media;
 if(mode==='video' && run?.artifacts.includes('recording.mp4')) {
  media=`<video controls preload="metadata" aria-label="${platformName(kind)} 运行录像" src="${artifactUrl(run.id,'recording.mp4')}"></video>`;
 } else if(mode==='image' && step?.screenshot) {
  media=`<button class="compare-image" data-evidence-run="${run.id}" data-evidence-file="${esc(step.screenshot)}" data-caption="${esc(platformName(kind)+' · '+step.title)}" aria-label="放大 ${platformName(kind)} 第 ${index+1} 步截图"><img src="${artifactUrl(run.id,step.screenshot)}" alt="${esc(platformName(kind)+' · '+step.title+' · 实际采集截图')}"></button>`;
 } else {
  const waiting=run?.status==='waiting_worker';
  const title=waiting?`等待 ${platformName(kind)} 节点`:!run?'尚未提交此平台':mode==='video'?'暂无运行录像':terminal(run.status)?'此步骤没有截图':'等待步骤执行';
  const detail=waiting?'尚未执行':!run?'上传此平台的应用文件后开始测试':mode==='video'?'录像会在运行结束并回传后显示':step?.detail || '执行后自动显示应用窗口画面';
  media=`<div class="evidence-placeholder">${icon(waiting?'terminal':'image')}<strong>${esc(title)}</strong><p>${esc(detail)}</p>${waiting||!run?`<a href="#strategy/${kind}${run?'/'+run.id:''}">导出 ${platformName(kind)} 执行包 →</a><br><a href="#nodes/${kind}">接入节点</a>`:''}</div>`;
 }
 return `<article class="card comparison-card" data-platform="${kind}"><header>${osMark(kind)}<div><h3>${platformName(kind)}</h3><small>${esc(node)}</small></div>${run?badge(run.status):'<span class="status-pill neutral">未提交</span>'}</header><div class="comparison-media">${media}</div><div class="comparison-meta"><span>${mode==='video'?'应用窗口录像':`第 ${index+1} 步 · ${step?esc(step.title):'等待验收场景'}`}</span>${step&&mode==='image'?badge(step.status):''}</div><div class="comparison-footer"><small>${run?esc(run.environment.os || (run.status==='waiting_worker'?'待记录系统环境':run.package.name)):esc(platform?.validation || '正在检查环境')}</small>${run?`<a href="#run/${run.id}">完整报告 ↗</a>`:''}</div>${run?.error?`<p class="comparison-error">${esc(run.error)}</p>`:''}</article>`;
}
function comparisonView(campaign) {
 const runs=campaign?.runs || [],steps=runs[0]?.steps || [],index=Math.min(state.compareStep??3,Math.max(0,steps.length-1));
 const media=state.compareMedia || 'image';
 const complete=runs.filter(r=>terminal(r.status)).length,passed=runs.filter(r=>r.status==='passed').length;
 return `<div class="comparison-summary"><div><h2>${campaign?esc(campaign.name):'暂无测试结果'}</h2><p>${campaign?`${complete} / ${runs.length} 个目标已结束 · ${passed} 个通过${campaign.passed?' · 全部通过':campaign.complete?' · 查看各平台结果':' · 等待其余结果'}`:'发起测试，或在下方创建 Notes 示例任务。'}</p></div>${campaign?`<a href="#matrix/${campaign.id}" class="text-link">查看对照 →</a>`:''}</div>${steps.length?`<div class="compare-controls"><div class="compare-steps" aria-label="选择对照步骤">${steps.map((s,i)=>`<button type="button" data-compare-step="${i}" aria-pressed="${i===index}" class="${i===index?'selected':''}"><span>${String(i+1).padStart(2,'0')}</span>${esc(s.title)}</button>`).join('')}</div><div class="media-switch" aria-label="证据类型"><button type="button" data-compare-media="image" aria-pressed="${media==='image'}">截图</button><button type="button" data-compare-media="video" aria-pressed="${media==='video'}">录像</button></div></div>`:''}<div class="comparison-grid">${['windows','macos','linux'].flatMap(kind=>{const targets=runs.filter(r=>r.platform===kind);return (targets.length?targets:[null]).map(run=>evidenceCard(kind,run,index,media));}).join('')}</div>`;
}
async function renderWorkspace() {
 const campaignId=state.campaigns[0]?.id;
 const campaign=campaignId?await api(`/api/campaigns/${campaignId}`):null;
 if(state.route!=='overview')return;
 const stamp=visualSignature([campaign,state.platforms,state.compareStep,state.compareMedia]);
 if(state.workspaceStamp===stamp)return;
 state.workspaceStamp=stamp;
 const ready=state.platforms.filter(p=>p.available).length;
 $('#platform-readiness').innerHTML=`<div class="readiness-total"><span>执行节点</span><small>${ready} / 3 个平台就绪</small></div><div class="readiness-platforms">${state.platforms.map(p=>`<a href="#nodes/${p.id}">${osMark(p.id)}<span><strong>${p.name}</strong><small class="${p.available?'ready-text':''}">${p.available?'就绪':'未连接'}</small></span><span class="readiness-dot ${p.available?'ready':''}"></span></a>`).join('')}</div>`;
 $('#workspace-evidence').innerHTML=comparisonView(campaign);
 $('#workspace-note').textContent=ready<3?'没有在线节点的平台，可导出执行包交给测试者。':'三个平台的执行节点已就绪。';
 const button=$('#campaign-demo');
 button.disabled=state.busy || state.health?.platform!=='windows';
 $('#campaign-demo-hint').textContent=state.health?.platform==='windows'?'创建三个平台的示例任务；没有节点的平台会等待。':'示例需要 Windows 控制台；也可以直接上传应用文件。';
}
async function startCampaignDemo() {
 if(state.busy)return;
 state.busy=true;const button=$('#campaign-demo');button.disabled=true;button.textContent='正在创建…';
 try {const campaign=await api('/api/demo/campaign',{method:'POST'});state.campaigns=[campaign,...state.campaigns];state.compareStep=3;state.compareMedia='image';location.hash=`matrix/${campaign.id}`;toast('示例任务已创建，无节点的平台等待执行');}
 catch(error){toast(error.message,true);}
 finally{state.busy=false;button.disabled=false;button.innerHTML=icon('play')+'创建示例任务';}
}
function setupPanel(kind) {
 const platform=state.platforms.find(p=>p.id===kind),config={
  windows:{needs:'在已登录、未锁屏的 Windows 桌面运行。一个桌面只启用一个节点。',commands:'python -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements.txt\npython -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name windows-node'},
  macos:{needs:'需要真实 Mac。给启动节点的终端 / Python 授予辅助功能和屏幕录制权限，再重启节点。原生适配器与内置示例尚待 Mac 实测。',commands:'python3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install -r requirements-macos.txt\npython -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name macos-node'},
  linux:{needs:'需要 Linux X11 桌面、D-Bus 和 AT-SPI。Wayland 暂不支持。下面以 Debian / Ubuntu 为例；原生适配器与内置示例尚待 Linux 实测。',commands:'sudo apt install python3-venv python3-gi gir1.2-atspi-2.0 gir1.2-gtk-3.0 at-spi2-core dbus-x11\npython3 -m venv --system-site-packages .venv\nsource .venv/bin/activate\npython -m pip install -r requirements-linux.txt\npython -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name linux-node'}
 }[kind];
 return `<section class="card node-setup"><div class="card-header"><h2>接入 ${platformName(kind)} 测试机</h2><span class="status-pill ${platform?.available?'good':'warn'}">${platform?.available?'已有就绪节点':'尚缺就绪节点'}</span></div><div class="card-body"><p>${config.needs}</p><ol><li>将本项目复制到目标机器，将控制台的 data/agent-token 通过可信方式保存为项目中的 node.token。</li><li>在目标机器另开终端建立私有转发；把 user@controller-host 替换为可访问控制台的 SSH 地址。<pre>ssh -N -L 8765:127.0.0.1:8765 user@controller-host</pre></li><li>在目标机器的桌面终端进入项目目录，依次执行：<pre id="node-command">${esc(config.commands)}</pre><button class="button secondary" data-copy-node>复制节点命令</button></li><li>保持节点运行。页面会自动更新连接状态，节点会领取该系统等待中的任务。</li></ol></div></section>`;
}
function initWorkspace() {
 $('#campaign-demo').addEventListener('click',startCampaignDemo);
 document.addEventListener('click',async event=>{
  const shot=event.target.closest('[data-evidence-run]');
  if(shot){$('#large-image').src=artifactUrl(shot.dataset.evidenceRun,shot.dataset.evidenceFile);$('#image-caption').textContent=shot.dataset.caption;$('#image-dialog').showModal();return;}
  const step=event.target.closest('[data-compare-step]'),media=event.target.closest('[data-compare-media]');
  if(step||media){if(step)state.compareStep=Number(step.dataset.compareStep);if(media)state.compareMedia=media.dataset.compareMedia;try{if(state.route==='overview')await renderWorkspace();else await renderMatrix();}catch(error){toast(error.message,true);}return;}
  if(event.target.closest('[data-copy-node]')){try{await navigator.clipboard.writeText($('#node-command').textContent);toast('节点命令已复制');}catch(error){toast(error.message,true);}}
 });
}
