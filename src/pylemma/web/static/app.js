const status = document.querySelector('#status');
const output = document.querySelector('#result');
const params = new URLSearchParams(location.search);
let target = params.get('challenge');
let current;
const el = (tag, text) => { const node = document.createElement(tag); node.textContent = text; return node; };
async function api(path, body) {
  const response = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your input and try again.');
  return data;
}
function button(label, action) { const node = el('button', label); node.type='button'; node.onclick=action; return node; }
function link(label, query) { const a=el('a',label); a.href='/?'+query; return a; }
function rounds(match, title) {
  const details=el('details',''); details.append(el('summary',title));
  details.append(el('p',`${match.combined} combined points · Cooperation: ${match.cooperation.join(' / ')} rounds`));
  for(const round of match.rounds) {
    details.append(el('p', `${round.round}. ${round.choices.join(' / ')} · ${round.points.join(' / ')} points`));
    details.append(el('p',round.reasons.join(' | ')));
  }
  output.append(details);
}
function showMachine(machine) {
  current=machine; output.hidden=false; output.replaceChildren(el('h2',machine.name),el('p',machine.blueprint.summary));
  const details=el('details',''); details.append(el('summary','Inspect the generated Python'),el('pre',machine.blueprint.code)); output.append(details);
  output.append(el('p','These rules were generated from: '+machine.strategy));
  const actions=el('div',''); actions.className='actions';
  actions.append(button('Copy challenge link', async()=>{
    try { await navigator.clipboard.writeText(location.origin+'/?challenge='+machine.id); status.textContent='Challenge link copied.'; }
    catch { status.textContent=location.origin+'/?challenge='+machine.id; }
  }),button('Revise these rules',()=>{
    document.querySelector('#name').value=machine.name; document.querySelector('#strategy').value=machine.strategy;
    document.querySelector('#strategy').focus();
  })); output.append(actions);
}
function showResult(data) {
  if(data.kind==='tournament') {
    showMachine(data.machine);
    const score=el('p',data.result.total+' tournament points'); score.className='score'; output.append(score);
    output.append(el('p','Fixed opponent set: trust-v1. Your score depends on this opponent set.'));
    data.result.matches.forEach(m=>rounds(m,`${m.opponent}: ${m.totals.join(' / ')} points`));
  } else {
    output.hidden=false; output.replaceChildren(el('h2',data.machines.map(m=>m.name).join(' vs ')));
    output.append(el('p',`${data.result.totals.join(' / ')} points · ${data.result.combined} combined`));
    rounds(data.result,'Inspect all ten rounds');
    data.machines.forEach(m=>output.append(link('Challenge '+m.name,'challenge='+m.id),el('br','')));
  }
  if (data.public_trace_url) {
    const trace=el('a','Inspect execution in Logfire'); trace.href=data.public_trace_url; trace.rel='noopener noreferrer'; output.append(trace);
  } else output.append(el('p','Execution is recorded in Logfire. Public trace links require operator review.'));
}
async function challenge(left,right) {
  status.textContent='The machines are playing…';
  const data=await api('/api/challenges',{left,right});
  location.assign('/?replay='+data.replay_id);
}
document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{document.querySelector('#strategy').value=b.dataset.example;});
document.querySelector('#builder').onsubmit=async(event)=>{
  event.preventDefault(); const submit=event.target.querySelector('[type=submit]'); submit.disabled=true;
  status.textContent='Generating your machine and testing it against three opponents…';
  try {
    const data=await api('/api/machines',{name:document.querySelector('#name').value,strategy:document.querySelector('#strategy').value,public_acknowledged:document.querySelector('#ack').checked});
    showResult({kind:'tournament',machine:data.machine,result:data.result});
    output.append(link('Open permanent replay','replay='+data.replay_id));
    history.replaceState(null,'','/?replay='+data.replay_id);
    status.textContent='Your machine is ready.';
    if(target) output.append(button('Challenge the invited machine',async()=>{try{await challenge(data.machine.id,target);}catch(e){status.textContent=e.message;}}));
  } catch(error) { status.textContent=error.message; } finally { submit.disabled=false; }
};
(async()=>{
  try {
    if(params.has('replay')) showResult(await api('/api/replays/'+encodeURIComponent(params.get('replay'))));
    else if(target) {
      const machine=await api('/api/machines/'+encodeURIComponent(target)); showMachine(machine);
      status.textContent=`Build your machine above to challenge ${machine.name}.`;
    }
  } catch(error) { status.textContent=error.message; }
})();
