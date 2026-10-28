/** Facts derived from completed outcomes. Never infer motives from choices. */
export const REFERENCES = [
  {name: 'Always cooperate', score: 81},
  {name: 'Always betray', score: 78},
];
export const POLICIES = {
  'The Optimist': 'Always cooperates.',
  'The Grudge Holder': 'Cooperates until your first betrayal. Then always betrays.',
  'The Opportunist': 'Betrays after your betrayal, or in rounds 3, 6, and 9. Otherwise, cooperates.',
};
export const label = choice => choice === 'cooperate' ? 'Cooperate' : 'Betray';

export function findings(match, names) {
  const rounds = match.rounds;
  if (!rounds.length) return [];
  const result = [];
  const first = rounds.find(r => r.choices.includes('betray'));
  if (!first) {
    result.push(`Both players cooperated in every round. Each earned ${rounds.length * 3} points.`);
    return result;
  }
  const firstNames = first.choices.flatMap((choice, side) => choice === 'betray' ? [names[side]] : []);
  result.push(`${firstNames.join(' and ')} ${firstNames.length === 2 ? 'both betrayed' : 'betrayed'} first, in round ${first.round}.`);
  const opponentFirst = rounds.find(r => r.choices[1] === 'betray');
  if (opponentFirst && opponentFirst.choices[0] === 'cooperate') {
    const response = rounds.find(r => r.round > opponentFirst.round && r.choices[0] === 'betray');
    if (response) {
      const count = rounds.filter(r => r.round < response.round && r.choices[1] === 'betray').length;
      result.push(`${names[0]} first betrayed in round ${response.round}, after ${count} earlier ${count === 1 ? 'betrayal' : 'betrayals'} by ${names[1]}.`);
    } else result.push(`${names[0]} kept cooperating after ${names[1]}'s first betrayal.`);
  }
  let streak = 0;
  for (let i = rounds.length - 1; i >= 0 && rounds[i].choices.every(c => c === 'betray'); i--) streak++;
  if (streak >= 2) result.push(`Both players betrayed in the last ${streak} rounds. Each earned only ${streak} points in those rounds.`);
  return result;
}

export function outcome(match, names) {
  if (match.totals[0] === match.totals[1]) return `A draw: ${match.totals[0]} points each.`;
  const side = match.totals[0] > match.totals[1] ? 0 : 1;
  return `${names[side]} earned ${match.totals[side]} points; ${names[1-side]} earned ${match.totals[1-side]}.`;
}

export function comparison(total, baseline = REFERENCES[0]) {
  const difference = total - baseline.score;
  if (!difference) return `Your player matched the ${baseline.score} points earned by a player that always cooperates.`;
  const amount = Math.abs(difference);
  return `Your player earned ${amount} ${amount === 1 ? 'point' : 'points'} ${difference > 0 ? 'more' : 'fewer'} than a player that always cooperates against these same opponents.`;
}

/** Select a factual round for inspection, without assigning intent. */
export function highlight(match, names) {
  const rounds = match.rounds;
  let conflict=0;
  for (const round of rounds) {
    if (round.choices.every(choice=>choice === 'cooperate')) {
      if (conflict >= 2) return {round:round.round,recovery:true,
        text:`Both players returned to cooperation in round ${round.round} after ${conflict} rounds without mutual cooperation.`};
      conflict=0;
    } else conflict++;
  }
  const afterThree = rounds.find((round, index) => round.choices[0] === 'cooperate' &&
    rounds.slice(0,index).filter(r=>r.choices[1] === 'betray').length >= 3);
  if (afterThree) return {round:afterThree.round,
    text:`${names[0]} cooperated in round ${afterThree.round} after at least three earlier betrayals by ${names[1]}.`};
  const first = rounds.find(r=>r.choices.includes('betray'));
  if (first) return {round:first.round, text:findings(match,names)[0]};
  return {round:1, text:`Both players cooperated in every round. Each earned ${rounds.length * 3} points.`};
}

export function shareText(machine, result) {
  const rule = machine.strategy.length > 80 ? machine.strategy.slice(0,77) + '…' : machine.strategy;
  const format=result.suite_version === 'arena-v2' ?
    `\n${(result.total / 200).toFixed(2)} points per round against the fixed Arena v2 opponents.` : '';
  return `${machine.name}: “${rule}”\n${result.total} points against ${result.matches.length} ${result.matches.length === 1 ? 'player' : 'players'} in Prisoner’s Pylemma.${format}\nCan your strategy do better?`;
}


/** Highlight only the already verified public-trace URL format. */
export function inspectionUrl(data, spanId) {
  if (!data.logfire_url) return null;
  if (data.logfire_access !== 'public' || !/^[a-f0-9]{16}$/i.test(spanId || '')) return data.logfire_url;
  const url = new URL(data.logfire_url);
  if (/^\/public-trace\/[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(url.pathname)) {
    url.searchParams.set('spanId',spanId);
  }
  return url.href;
}


/** Prefer a recorded recovery over an arbitrary early betrayal. */
export function featuredDecision(matches,name) {
  const choices=matches.map(match=>{
    const selected=highlight(match,[name,match.opponent]);
    return {...selected,opponent:match.opponent,
      spanId:match.rounds.find(round=>round.round === selected.round)?.span_id};
  });
  return choices.find(choice=>choice.recovery) ||
    choices.find((choice,index)=>matches[index].rounds.some(round=>round.choices.includes('betray'))) || choices[0];
}
