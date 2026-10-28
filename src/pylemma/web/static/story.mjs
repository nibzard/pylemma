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
    result.push('Both players cooperated in every round. Each earned 30 points.');
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
