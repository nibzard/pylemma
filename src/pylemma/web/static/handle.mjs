export function normalizeHandle(value) {
  const handle = value.trim();
  return !handle || handle.startsWith('@') ? handle : '@' + handle;
}
