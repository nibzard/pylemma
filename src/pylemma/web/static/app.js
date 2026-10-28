import { REFERENCES, POLICIES, label, findings, outcome, comparison } from './story.mjs';

const $ = selector => document.querySelector(selector);
const status = $('#status');
const shared = $('#shared');
const review = $('#review');
const params = new URLSearchParams(location.search);
const targetId = params.get('challenge');
let target = null;
let activeMachine = null;
let activeReplay = params.get('replay');
let previousReplay = params.get('compare');
let submitting = false;

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
async function api(path, body) {
  const response = await fetch(path, body ? {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),
  } : {});
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The game server could not respond. Try again shortly.'); }
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your rules and try again.');
  }
  return data;
}
async function run(node, action, waiting) {
  if (submitting) return;
  submitting = true;
  node.disabled = true;
  message(waiting);
  try { await action(); }
  catch (error) { message(error.message, true); }
  finally { submitting = false; node.disabled = false; }
}
function showBuilder(machine) {
  $('#create').hidden = false;
  review.hidden = true;
  if (machine) {
    $('#name').value = machine.name;
    $('#strategy').value = machine.strategy;
    previousReplay = activeReplay;
  }
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
async function copyChallenge(machine, control) {
  const url = location.origin + '/?' + new URLSearchParams({challenge:machine.id});
  try {
    await navigator.clipboard.writeText(url);
    control.textContent = 'Challenge link copied';
    message('Challenge link copied. Send it to someone and see how their player responds.');
  } catch { message('Your challenge link: ' + url, true); }
}
function traceDetails(data, container) {
  if (data.public_trace_url) {
    const node = el('a', 'Inspect this game in Logfire');
    node.href = data.public_trace_url;
    node.rel = 'noopener noreferrer';
    container.append(node, el('p', 'See the generated code, the information each player received, and the choices it returned.', 'small'));
  }
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
  if (data.kind === 'tournament') {
    activeMachine = data.machine;
    summary.append(el('h1', data.machine.name));
    const score = el('p', String(data.result.total), 'score');
    score.append(el('span', 'points across three matches'));
    summary.append(score, el('p', data.machine.blueprint.summary));
    shared.append(summary);
    if (data.result.suite_version === 'trust-v1' && data.result.rules_version === 'pd-v1') {
      shared.append(refsView(data.result.total));
    }
    const actions = el('div', undefined, 'actions');
    const share = button('Challenge a friend', () => copyChallenge(data.machine, share));
    actions.append(button('Change one rule and compare', () => showBuilder(data.machine), 'primary'), share);
    shared.append(actions, el('h2', 'Where the points came from'));
    for (const match of data.result.matches) {
      shared.append(matchView(match, [data.machine.name, match.opponent], POLICIES[match.opponent]));
    }
    shared.append(technical(data.machine));
    void previousComparison(data);
  } else {
    activeMachine = null;
    const names = data.machines.map(machine => machine.name);
    const equal = data.result.totals[0] === data.result.totals[1];
    const winner = names[data.result.totals[0] > data.result.totals[1] ? 0 : 1];
    summary.append(el('h1', equal ? 'A draw. What would you change?' : `${winner} earned more points.`));
    summary.append(el('p', names.join(' vs '), 'lead'));
    shared.append(summary, matchView(data.result, names));
    const actions = el('div', undefined, 'actions');
    data.machines.forEach(machine => actions.append(link('Challenge ' + machine.name, {challenge:machine.id})));
    shared.append(actions);
    data.machines.forEach(machine => {
      const panel = el('div', undefined, 'panel');
      panel.append(el('h3', machine.name + "'s rules"), el('p', machine.blueprint.summary), technical(machine));
      shared.append(panel);
    });
  }
  traceDetails(data, shared);
  shared.append(el('p', 'These points describe this game. They do not measure intelligence or real-world trustworthiness.', 'small'));
  message('');
}
async function saveResult(data, kind) {
  activeReplay = data.replay_id;
  const values = {replay:activeReplay};
  if (previousReplay && kind === 'tournament') values.compare = previousReplay;
  history.replaceState(null, '', '/?' + new URLSearchParams(values));
  if (kind === 'tournament') showResult({kind, machine:data.machine, result:data.result});
  else showResult(await api('/api/replays/' + encodeURIComponent(activeReplay)));
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
  else review.append(el('p', 'Your player will play ten rounds against each of three opponents with different rules. Your score adds all thirty rounds.'));
  const actions = el('div', undefined, 'actions');
  const confirm = button(target ? 'Use these rules and challenge' : 'Use these rules and play', () => run(confirm, async () => {
    if (target) {
      const data = await api('/api/challenges', {left:machine.id, right:target.id});
      await saveResult(data, 'challenge');
    } else {
      const data = await api('/api/tournaments', {machine_id:machine.id});
      await saveResult(data, 'tournament');
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
  panel.append(el('h2', machine.name + "'s rules"), el('p', machine.blueprint.summary, 'lead'),
    el('p', 'Create a player to face it for ten rounds. The player with more points wins. Equal scores mean a draw.'));
  shared.append(panel);
  const actions = el('div', undefined, 'actions');
  actions.append(button('Create a challenger', () => showBuilder(), 'primary'), button('Learn the choices', showLesson));
  shared.append(actions, technical(machine));
}
function showLesson() {
  $('#learn').hidden = false;
  $('#lesson-title').setAttribute('tabindex', '-1');
  focus($('#lesson-title'));
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
      public_acknowledged:$('#ack').checked, preview:true,
    });
    const values = {player:data.machine.id};
    if (target) values.challenge = target.id;
    if (previousReplay) values.compare = previousReplay;
    history.replaceState(null, '', '/?' + new URLSearchParams(values));
    preview(data.machine);
  }, 'Turning your description into a player and checking that its rules can run…');
};
showDemo();
(async () => {
  try {
    if (params.has('replay') || targetId || params.has('player')) {
      sharedLayout();
      message('Opening the shared player or result…');
    }
    if (targetId) target = await api('/api/machines/' + encodeURIComponent(targetId));
    if (params.has('replay')) {
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
