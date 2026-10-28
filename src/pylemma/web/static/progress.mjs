/** Stages describe completed HTTP boundaries, never estimated game progress. */
export const STAGES = ['Build and check rules', 'Play the game', 'Open the result'];
export function requestStage(path, method) {
  if (method === 'POST' && path === '/api/machines') return 0;
  if (method === 'POST' && ['/api/arena','/api/challenges','/api/tournaments'].includes(path)) return 1;
  if (method === 'GET' && path.startsWith('/api/replays/')) return 2;
  return null;
}
export function requestError(path, status, detail) {
  if (status === 429) return typeof detail === 'string' ? detail : 'The game server is busy. Wait a moment, then try again.';
  if (typeof detail === 'string' && status && status !== 404) return detail;
  if (status === 404) return 'This player or result is not available. Check the link, or try again shortly.';
  if (path.startsWith('/api/replays/')) return 'The saved result could not be opened. Reload this page to try again.';
  if (path === '/api/machines') return 'The connection was lost while building your player. Your description is still here. Check your connection before trying again.';
  return 'The game server could not respond. Your player is saved. Wait a moment, then retry the game.';
}
