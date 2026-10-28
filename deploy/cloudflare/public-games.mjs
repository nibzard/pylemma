/** Public discovery requires explicit consent from every visitor participant. */
export function publicEntry(id, data) {
  const result = data.result || {};
  let machines, scores;
  const roundsPerMatch=data.kind === 'arena' && result.suite_version === 'arena-v2' ? 20 : 10;
  if (['tournament','arena'].includes(data.kind)) {
    machines = [data.machine || {}];
    if (!Array.isArray(result.matches) || result.matches.length !== (data.kind === 'arena' ? 10 : 3) ||
        result.matches.some(match => match.rounds?.length !== roundsPerMatch) ||
        result.rules_version !== 'pd-v1' || !(data.kind === 'arena' ? ['arena-v1','arena-v2'] : ['trust-v1']).includes(result.suite_version)) return null;
    scores = [result.total];
  } else if (data.kind === 'challenge') {
    machines = data.machines || [];
    if (machines.length !== 2 || result.rounds?.length !== 10 || result.totals?.length !== 2) return null;
    scores = result.totals;
  } else return null;
  if (machines.some(machine => machine.public_listing !== true) ||
      scores.some(score => !Number.isInteger(score) || score < 0 || score > (data.kind === 'arena' ? 50 * roundsPerMatch : 150))) return null;
  return {replay_id:id, kind:data.kind,
    players:machines.map(machine => ({id:machine.id, name:machine.name, strategy:machine.strategy ?? ""})),
    scores, suite_version:result.suite_version ?? null, rounds_per_match:roundsPerMatch, created_at:data.created_at ?? null};
}

export function publicPage(entries, ranked, offset, limit) {
  const rows = entries.filter(row=>!ranked || row.kind === 'tournament').map(row=>({...row}));
  if (ranked) {
    rows.sort((a,b)=>b.scores[0]-a.scores[0] || a.replay_id.localeCompare(b.replay_id));
    let rank=0, previous=null;
    rows.forEach((row,index)=>{
      if (row.scores[0] !== previous) rank=index+1;
      previous=row.scores[0]; row.rank=rank;
    });
  } else rows.sort((a,b)=>(Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0) ||
    b.replay_id.localeCompare(a.replay_id));
  const end=offset+limit;
  return {entries:rows.slice(offset,end), total:rows.length, next_offset:end<rows.length?end:null};
}
