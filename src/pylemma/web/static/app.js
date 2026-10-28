import { STAGES, requestStage, requestError, failureReport } from './progress.mjs';
import { REFERENCES, POLICIES, label, findings, outcome, comparison, highlight, shareText, inspectionUrl } from './story.mjs';

const $ = selector => document.querySelector(selector);
const status = $('#status');
const shared = $('#shared');
const review = $('#review');
const params = new URLSearchParams(location.search);
const targetId = params.get('challenge');
const referral = params.get('ref') === 'share' ? targetId : null;
let target = null;
let activeMachine = null;
let activeReplay = params.get('replay');
let previousReplay = params.get('compare');
let submitting = false;
let progressTimer = null;
let progressStarted = 0;
let progressStage = null;
function updateProgress(stage) {
  if (stage === null) return;
  progressStage = stage;
  const box = $('#progress');
  const wasHidden = box.hidden;
  box.hidden = false;
  if (wasHidden) box.scrollIntoView({block:'center'});
  $('#progress-title').textContent = STAGES[stage];
  $('#progress-steps').replaceChildren(...STAGES.map((title,index)=>{
    const item = el('li', (index < stage ? '✓ ' : '') + title);
    if (index === stage) item.setAttribute('aria-current','step');
    return item;
  }));
  $('#progress-note').textContent = stage === 0 ?
    'The server is generating your code and checking that it can run. This can take a little time.' :
    stage === 1 ? 'Your saved rules are playing. Each match has ten rounds.' : 'The game is complete. Opening its saved result.';
}
function startProgress() {
  progressStarted = Date.now();
  $('#progress-time').textContent = '';
  progressTimer = setInterval(()=>{
    const seconds = Math.floor((Date.now()-progressStarted)/1000);
    $('#progress-time').textContent = `${seconds} seconds elapsed`;
    if (seconds >= 15 && progressStage !== 2) $('#progress-note').textContent =
      'Still waiting for the server. Keep this tab open. You do not need to submit again.';
  },1000);
}
function stopProgress() {
  clearInterval(progressTimer); progressTimer = null; progressStage = null;
  $('#progress').hidden = true;
}

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action, className) {
  const node = el('button', text, className);
  node.type = 'button';
  node.onclick = action;
  return node;
}
function link(text, values) {
  const node = el('a', text);
  node.href = '/?' + new URLSearchParams(values);
  return node;
}
function focus(node) {
  node.scrollIntoView({block:'start'});
  node.focus({preventScroll:true});
}
function message(text, isError = false) {
  status.textContent = text;
  if (isError) status.scrollIntoView({block:'center'});
}
function apiFailure(path, requestId, failure, status, detail) {
  // Best effort only. A failed report must never retry the original operation.
  void fetch('/api/diagnostics',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(failureReport(path,requestId,failure,status)),keepalive:true}).catch(()=>{});
  return new Error(requestError(path,status,detail) + ' Reference: ' + requestId);
}
async function api(path, body) {
  const requestId = crypto.randomUUID();
  if (submitting) updateProgress(requestStage(path,body ? 'POST' : 'GET'));
  let response;
  try {
    response = await fetch(path, body ? {
      method:'POST', headers:{'Content-Type':'application/json','X-Request-ID':requestId}, body:JSON.stringify(body),
    } : {headers:{'X-Request-ID':requestId}});
  } catch { throw apiFailure(path,requestId,'network',0); }
  let data;
  try { data = await response.json(); }
  catch { throw apiFailure(path,requestId,'invalid_response',response.status); }
  if (!response.ok) throw apiFailure(path,requestId,'http',response.status,data.detail);
  return data;
}
async function run(node, action, waiting) {
  if (submitting) return;
  submitting = true;
  node.disabled = true;
  message(waiting);
  startProgress();
  status.scrollIntoView({block:'center'});
  try { await action(); }
  catch (error) { message(error.message, true); }
  finally { stopProgress(); submitting = false; node.disabled = false; }
}
function showBuilder(machine) {
  $('#create').hidden = false;
  review.hidden = true;
  if (machine) {
    $('#name').value = machine.name;
    $('#strategy').value = machine.strategy;
    $('#listed').checked = machine.public_listing === true;
    previousReplay = activeReplay;
  }
  $('#builder [type=submit]').textContent = target ? 'Challenge this strategy' : 'Enter the arena';
  focus($('#strategy'));
}
function sharedLayout() {
  $('#intro').hidden = true;
  $('#create').hidden = true;
  $('#learn').hidden = true;
  shared.hidden = false;
}
function details(title, content) {
  const node = el('details');
  node.append(el('summary', title), content);
  return node;
}
function technical(machine) {
  const body = el('div');
  body.append(el('p', "AI generated this Python from the player's rules. Monty runs each decision in a fresh sandbox."));
  body.append(el('pre', machine.blueprint.code));
  return details('How this player works', body);
}
function choiceCard(name, choice, points) {
  const card = el('div', undefined, 'choice ' + choice);
  card.append(el('span', name, 'who'), el('strong', label(choice)),
    el('span', `${points} ${points === 1 ? 'point' : 'points'}`, 'points'));
  return card;
}
function track(event) {
  if (!activeReplay) return;
  void fetch('/api/events', {method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({event,replay_id:activeReplay}),keepalive:true}).catch(()=>{});
}
function sharing(machine, result) {
  const card = el('div', undefined, 'panel share-card');
  card.append(el('p', "Prisoner's Pylemma", 'eyebrow'), el('h2',machine.name),
    el('p',machine.strategy.length > 160 ? machine.strategy.slice(0,157)+'…' : machine.strategy),
    el('p',`${result.total} points against ${result.matches.length} ${result.matches.length === 1 ? 'player' : 'players'}.`, 'lead'));
  const url = location.origin + '/?' + new URLSearchParams({challenge:machine.id,ref:'share'});
  const post = el('a','Share on X','inspect-button');
  post.href = 'https://twitter.com/intent/tweet?' + new URLSearchParams({text:shareText(machine,result),url});
  post.target = '_blank'; post.rel = 'noopener noreferrer';
  post.onclick = () => track('share_click');
  const copy = button('Copy challenge link',()=>copyChallenge(machine,copy));
  card.append(post,document.createTextNode(' '),copy);
  return card;
}
async function copyChallenge(machine, control) {
  track('share_click');
  const url = location.origin + '/?' + new URLSearchParams({challenge:machine.id,ref:'share'});
  try {
    await navigator.clipboard.writeText(url);
    control.textContent = 'Challenge link copied';
    message('Challenge link copied. Send it to someone and see how their player responds.');
  } catch { message('Your challenge link: ' + url, true); }
}
function traceDetails(data, container, selected) {
  if (selected) container.append(el('p',selected.text,'finding'));
  const action = data.logfire_url ? el('a', selected ? 'Inspect this decision in Logfire' : 'Inspect in Logfire', 'inspect-button') :
    el('button', selected ? 'Inspect this decision in Logfire' : 'Inspect in Logfire');
  if (data.logfire_url) {
    action.href = inspectionUrl(data, selected?.spanId);
    action.target = '_blank';
    action.rel = 'noopener noreferrer';
    action.onclick = () => track('inspection_click');
  } else {
    action.type = 'button';
    action.disabled = true;
  }
  const box = el('div', undefined, 'inspection');
  box.append(action, el('p', data.logfire_access === 'public' ?
    'Open the complete game trace. No Logfire account is needed.' :
    data.logfire_url ? 'A Logfire account with access to this project is required.' :
    'The Logfire link for this game is not available.', 'small'));
  if (selected) box.append(el('p', `Find round ${selected.round} in the match with ${selected.opponent}.`, 'small'));
  box.append(el('p', 'Inspect the information each player received, its returned choices, and execution timing.', 'small'));
  if (data.logfire_access !== 'public') {
    const example = el('a','Inspect a reviewed example in Logfire');
    example.href = 'https://logfire-eu.pydantic.dev/public-trace/44e57f30-c25a-47fe-b85f-5db1d0604010?spanId=4ed36f7dff63d8fe';
    example.target = '_blank'; example.rel = 'noopener noreferrer';
    example.onclick = () => track('example_inspection_click');
    box.append(example,el('p', 'This separate recorded tournament opens without a Logfire account.', 'small'));
  }

  container.append(box);
}

function matchView(match, names, policy) {
  const card = el('article', undefined, 'panel');
  card.append(el('h3', names.join(' vs ')));
  if (policy) card.append(el('p', policy, 'small'));
  card.append(el('p', outcome(match, names)));
  for (const fact of findings(match, names)) card.append(el('p', fact, 'finding'));
  card.append(el('p', `Together, the players earned ${match.combined} points. Both cooperating in all ten rounds would earn 60.`));
  const body = el('div');
  body.append(el('p', 'Earlier rounds are the only history a player can see. Each pair of choices is revealed together.', 'small'));
  for (const round of match.rounds) {
    const row = el('div', undefined, 'round');
    row.append(el('h4', 'Round ' + round.round));
    const pair = el('div', undefined, 'choice-pair');
    pair.append(...names.map((name, side) => choiceCard(name, round.choices[side], round.points[side])));
    row.append(pair);
    const reasons = el('div');
    reasons.append(...names.map((name, side) => el('p', `${name}: ${round.reasons[side]}`)));
    row.append(details('Reasons returned by the players', reasons));
    body.append(row);
  }
  card.append(details('See all ten rounds', body));
  return card;
}
function refsView(total) {
  const box = el('div', undefined, 'panel');
  box.append(el('h3', 'What does that score mean?'), el('p', comparison(total)));
  for (const reference of [{name:'This player', score:total}, ...REFERENCES]) {
    const row = el('div', undefined, 'reference');
    row.append(el('span', reference.name), el('strong', String(reference.score)));
    const meter = el('meter');
    meter.min = 0; meter.max = Math.max(150, total); meter.value = reference.score;
    meter.setAttribute('aria-label', `${reference.name}: ${reference.score} points`);
    row.append(meter); box.append(row);
  }
  box.append(el('p', 'Each score covers ten rounds against each of the same three opponents. Different opponents can favor different rules.', 'small'));
  return box;
}
async function previousComparison(data) {
  if (!previousReplay || previousReplay === activeReplay) return;
  try {
    const before = await api('/api/replays/' + encodeURIComponent(previousReplay));
    if (before.kind !== 'tournament' || before.result.suite_version !== data.result.suite_version ||
        before.result.rules_version !== data.result.rules_version) return;
    const difference = data.result.total - before.result.total;
    const text = difference === 0 ? 'Both versions earned the same score.' :
      `This version earned ${Math.abs(difference)} ${difference > 0 ? 'more' : 'fewer'} points.`;
    const box = el('p', `Your previous version earned ${before.result.total} points. ${text}`, 'finding');
    box.append(document.createTextNode(' '), link('Compare the previous result', {replay:previousReplay}));
    $('#result-summary').append(box);
  } catch { /* An unavailable earlier replay does not hide the current result. */ }
}
function showResult(data) {
  sharedLayout();
  review.hidden = true;
  shared.replaceChildren(el('p', 'The results', 'eyebrow'));
  const summary = el('div'); summary.id = 'result-summary';
  if (['tournament','arena'].includes(data.kind)) {
    activeMachine = data.machine;
    summary.append(el('h1', data.machine.name));
    const score = el('p', String(data.result.total), 'score');
    score.append(el('span', `points across ${data.result.matches.length} matches`));
    summary.append(score, el('p', data.machine.blueprint.summary));
    shared.append(summary);
    const featured = data.result.matches.find(m=>m.rounds.some(r=>r.choices.includes('betray'))) || data.result.matches[0];
    const selected = {...highlight(featured,[data.machine.name,featured.opponent]),opponent:featured.opponent};
    selected.spanId = featured.rounds.find(r=>r.round === selected.round)?.span_id;
    traceDetails(data, summary, selected);
    if (data.kind === 'arena') {
      const presets = data.result.matches.filter(m=>m.preset).length;
      summary.append(el('p', `Ten rounds per opponent. ${presets} of the ten opponents are presets.`, 'small'),
        el('p','Entrants can face different opponents. These scores are not a global ranking.','small'));
    }
    if (data.result.suite_version === 'trust-v1' && data.result.rules_version === 'pd-v1') {
      shared.append(refsView(data.result.total));
    }
    const actions = el('div', undefined, 'actions');
    actions.append(button('Revise strategy', () => showBuilder(data.machine), 'primary'));
    shared.append(actions, sharing(data.machine,data.result), el('h2', 'Where the points came from'));
    for (const match of data.result.matches) {
      shared.append(matchView(match, [data.machine.name, match.opponent], match.preset === false ? undefined : POLICIES[match.opponent]));
    }
    shared.append(technical(data.machine));
    if (data.kind === 'tournament') void previousComparison(data);
  } else {
    activeMachine = null;
    const names = data.machines.map(machine => machine.name);
    const equal = data.result.totals[0] === data.result.totals[1];
    const winner = names[data.result.totals[0] > data.result.totals[1] ? 0 : 1];
    summary.append(el('h1', equal ? 'A draw. What would you change?' : `${winner} earned more points.`));
    summary.append(el('p', names.join(' vs '), 'lead'));
    shared.append(summary);
    const selected = {...highlight(data.result,names),opponent:names[1]};
    selected.spanId = data.result.rounds.find(r=>r.round === selected.round)?.span_id;
    traceDetails(data, summary, selected);
    shared.append(matchView(data.result, names), sharing(data.machines[0],{
      total:data.result.totals[0],matches:[data.result],
    }));
    const actions = el('div', undefined, 'actions');
    data.machines.forEach(machine => actions.append(link('Challenge ' + machine.name, {challenge:machine.id})));
    shared.append(actions);
    data.machines.forEach(machine => {
      const panel = el('div', undefined, 'panel');
      panel.append(el('h3', machine.name + "'s rules"), el('p', machine.blueprint.summary), technical(machine));
      shared.append(panel);
    });
  }
  const listed = ['tournament','arena'].includes(data.kind) ? data.machine.public_listing === true :
    data.machines.every(machine => machine.public_listing === true);
  shared.append(el('p', listed ? 'This completed game is listed publicly.' : 'This game is unlisted. It does not appear in public game lists.', 'small'));
  shared.append(link('See recent arena results', {leaderboard:'1'}));

  shared.append(el('p', 'These points describe this game. They do not measure intelligence or real-world trustworthiness.', 'small'));
  message('');
}
async function saveResult(data, kind) {
  activeReplay = data.replay_id;
  const values = {replay:activeReplay};
  if (previousReplay && kind === 'tournament') values.compare = previousReplay;
  history.replaceState(null, '', '/?' + new URLSearchParams(values));
  showResult(await api('/api/replays/' + encodeURIComponent(activeReplay)));
  focus(shared);
}
function preview(machine) {
  sharedLayout();
  shared.hidden = true;
  activeMachine = machine;
  $('#create').hidden = true;
  review.hidden = false;
  review.replaceChildren(el('p', 'Check before you play', 'eyebrow'), el('h2', machine.name + "'s rules"),
    el('p', machine.blueprint.summary, 'lead'), el('p', 'Does this match what you meant? Check the summary and change your description if it does not.'));
  if (target) review.append(el('p', 'Your player will face ' + target.name + ' for ten rounds.'));
  else review.append(el('p', 'Your player faces ten recent public players. Presets fill any empty slots.'));
  const actions = el('div', undefined, 'actions');
  const confirm = button(target ? 'Use these rules and challenge' : 'Use these rules and play', () => run(confirm, async () => {
    if (target) {
      const data = await api('/api/challenges', {left:machine.id, right:target.id, referral});
      await saveResult(data, 'challenge');
    } else {
      const data = await api('/api/arena', {machine_id:machine.id});
      await saveResult(data, 'arena');
    }
  }, 'Playing your confirmed rules. Each pair of choices is revealed together…'), 'primary');
  actions.append(confirm, button('Change my description', () => showBuilder(machine)));
  review.append(actions, el('p', 'Playing this stored version makes no new AI request.', 'small'), technical(machine));
  message('Your player is ready for you to check.');
  focus(review);
}
function invitation(machine) {
  target = machine;
  sharedLayout();
  shared.replaceChildren(el('p', 'You have been challenged', 'eyebrow'), el('h1', `Can your player beat ${machine.name}?`));
  const panel = el('div', undefined, 'panel');
  panel.append(el('h2', machine.name + "'s rules"), el('p', machine.strategy, 'lead'),
    el('p', 'Create a player to face it for ten rounds. The player with more points wins. Equal scores mean a draw.'));
  shared.append(panel);
  const actions = el('div', undefined, 'actions');
  actions.append(button('Challenge this strategy', () => showBuilder(), 'primary'), button('Learn the choices', showLesson));
  shared.append(actions, technical(machine));
}
function showLesson() {
  $('#learn').hidden = false;
  $('#lesson-title').setAttribute('tabindex', '-1');
  focus($('#lesson-title'));
}

async function leaderboard() {
  sharedLayout();
  const all = params.get('view') === 'all';
  const rawOffset = Number(params.get('offset') || 0);
  const offset = Number.isInteger(rawOffset) && rawOffset >= 0 ? rawOffset : 0;
  shared.replaceChildren(el('p', 'The public games', 'eyebrow'),
    el('h1', all ? 'Every public game.' : 'Recent arena results'));
  const actions = el('div', undefined, 'actions');
  actions.append(link('Recent arena results', {leaderboard:'1'}),
    link('All public games', {leaderboard:'1',view:'all'}),
    button('Create your player', () => showBuilder(), 'primary'));
  actions.querySelectorAll('a')[all ? 1 : 0].setAttribute('aria-current', 'page');
  shared.append(actions);
  shared.append(el('p', all ?
    'Completed public arenas, tournaments, and challenges, newest first.' :
    'One result per strategy, newest first. Entrants can face different opponents. These scores are not a global ranking.'));
  shared.append(el('p', 'Only players that permit public listing appear here. Existing unlisted games stay unlisted.', 'small'));
  message('Loading public games…');
  const data = await api(`${all ? '/api/games' : '/api/arena'}?offset=${offset}&limit=20`);
  message('');
  if (!data.entries.length) {
    shared.append(el('p', data.total ? 'There are no games on this page.' :
      'No completed public games yet. Create a player with public listing enabled to add the first one.', 'panel'));
  } else {
    shared.append(el('p', `${data.total} completed public ${data.total === 1 ? 'game' : 'games'}.`, 'small'));
    const box = el('div', undefined, 'board-scroll');
    box.tabIndex = 0;
    box.setAttribute('role', 'region');
    box.setAttribute('aria-label', 'Scrollable table of public games');
    const table = el('table', undefined, 'board');
    table.append(el('caption', all ? 'All completed public games' : 'Recent arena results · arena-v1 · pd-v1'));
    const head = el('tr');
    for (const title of all ? ['Game', 'Players', 'Points', 'Played', 'Replay'] : ['Game', 'Player', 'Points', 'Replay', 'Challenge']) {
      const th = el('th', title); th.scope = 'col'; head.append(th);
    }
    const thead = el('thead'); thead.append(head); table.append(thead);
    const body = el('tbody');
    for (const entry of data.entries) {
      const row = el('tr');
      row.append(el('td', all ? ({arena:'Arena',tournament:'Tournament',challenge:'Challenge'}[entry.kind]) : 'Arena'),
        el('td', entry.players.map(player => player.name).join(' vs ')),
        el('td', entry.scores.join(' / ')));
      if (all) {
        const played = el('td');
        const stamp = entry.created_at ? new Date(entry.created_at) : null;
        const time = el('time', stamp ? stamp.toLocaleString(undefined, {dateStyle:'medium',timeStyle:'short'}) : 'Time unavailable');
        if (entry.created_at) time.dateTime = entry.created_at;
        played.append(time); row.append(played);
      }
      const replay = el('td'); replay.append(link('Watch game', {replay:entry.replay_id})); row.append(replay);
      if (!all) {
        const challenge = el('td'); challenge.append(link('Challenge', {challenge:entry.players[0].id})); row.append(challenge);
      }
      body.append(row);
    }
    table.append(body); box.append(table); shared.append(box);
  }
  const pages = el('div', undefined, 'actions');
  const values = {leaderboard:'1'};
  if (all) values.view='all';
  if (offset) pages.append(link('Previous page', {...values,offset:String(Math.max(0,offset-20))}));
  if (data.next_offset !== null) pages.append(link('Next page', {...values,offset:String(data.next_offset)}));
  shared.append(pages);
}

const scenes = [
  {choices:['cooperate','cooperate'], points:[3,3], title:'You both cooperate.',
    text:'You each earn 3 points. Working together pays both players.', next:'What if you betray?'},
  {choices:['betray','cooperate'], points:[5,0], title:'You betray. They cooperate.',
    text:'You earn 5 points; they earn nothing. Betrayal pays you more this round.', next:'What if they betray too?'},
  {choices:['betray','betray'], points:[1,1], title:'Now you both betray.',
    text:'You each earn only 1 point. Can you protect yourself without losing the rewards of cooperation?', next:'Try the example again'},
];
let scene = 0;
function showDemo() {
  const item = scenes[scene];
  $('#demo-choices').replaceChildren(...['You', 'Other player'].map((name, side) => choiceCard(name, item.choices[side], item.points[side])));
  $('#demo-explanation').replaceChildren(el('h3', item.title), el('p', item.text));
  $('#demo-next').textContent = item.next;
}
$('#demo-next').onclick = () => { scene = (scene + 1) % scenes.length; showDemo(); };
$('#help').onclick = showLesson;
$('#try-demo').onclick = showLesson;
$('#start').onclick = () => showBuilder();
for (const example of document.querySelectorAll('[data-example]')) {
  example.onclick = () => { $('#strategy').value = example.dataset.example; $('#name').value = example.dataset.name; };
}
$('#builder').onsubmit = event => {
  event.preventDefault();
  const submit = event.target.querySelector('[type=submit]');
  void run(submit, async () => {
    const data = await api('/api/machines', {
      name:$('#name').value, strategy:$('#strategy').value,
      public_acknowledged:$('#ack').checked, public_listing:$('#listed').checked, preview:true,
    });
    const values = {player:data.machine.id};
    if (target) values.challenge = target.id;
    if (referral) values.ref = 'share';
    if (previousReplay) values.compare = previousReplay;
    history.replaceState(null, '', '/?' + new URLSearchParams(values));
    if ($('#preview-first').checked) {
      preview(data.machine);
    } else {
      activeMachine = data.machine;
      message(target ? 'Playing your challenge…' : 'Your player is facing ten opponents…');
      try {
        const result = target ? await api('/api/challenges',{left:data.machine.id,right:target.id,referral}) :
          await api('/api/arena',{machine_id:data.machine.id});
        await saveResult(result,target ? 'challenge' : 'arena');
      } catch (error) {
        if (!activeReplay || !location.search.includes('replay=')) preview(data.machine);
        throw error;
      }
    }
  }, 'Building your player and checking its rules…');
};
showDemo();
(async () => {
  try {
    if (params.has('leaderboard') || params.has('replay') || targetId || params.has('player')) {
      sharedLayout();
      message('Opening the shared player or result…');
    }
    if (targetId) target = await api('/api/machines/' + encodeURIComponent(targetId));
    if (params.has('leaderboard')) {
      await leaderboard();
    } else if (params.has('replay')) {
      showResult(await api('/api/replays/' + encodeURIComponent(params.get('replay'))));
    } else if (params.has('player')) {
      preview(await api('/api/machines/' + encodeURIComponent(params.get('player'))));
    } else if (target) {
      invitation(target); message('');
    }
  } catch (error) {
    sharedLayout();
    shared.replaceChildren(el('h1', 'This game could not be opened.'), el('p', error.message), link('Create your own player', {}));
    message('');
  }
})();
