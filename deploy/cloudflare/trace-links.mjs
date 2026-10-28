/** Only reviewed sharing links are described as public. */
const HOSTS = new Set(['logfire.pydantic.dev','logfire-us.pydantic.dev','logfire-eu.pydantic.dev']);
const TRACE = /^[a-fA-F0-9]{32}$/;
const validSource = value => typeof value === 'string' && value.length <= 2048 &&
  !/[\x00-\x20\x7f-\uffff%\\]/.test(value) && HOSTS.has(value.match(/^https:\/\/([^/]+)\//)?.[1]);
export function inspectLink(data, projectUrl, publicUrls={}) {
  const result = {...data,logfire_url:null,logfire_access:'unavailable'};
  if (typeof data.trace_id !== 'string' || !TRACE.test(data.trace_id)) return result;
  const publicUrl = data.public_trace_url || publicUrls[data.trace_id];
  if (validSource(publicUrl)) {
    try {
      const url = new URL(publicUrl);
      const highlight = /^\/public-trace\/[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$/.test(url.pathname) &&
        /^\?spanId=[a-fA-F0-9]{16}$/.test(url.search);
      if (url.protocol === 'https:' && HOSTS.has(url.host) && !url.username && !url.password &&
          url.pathname !== '/' && (!url.search || highlight) && !url.hash) {
        return {...result, logfire_url:publicUrl,logfire_access:'public'};
      }
    } catch { /* Invalid public references cannot grant public access. */ }
  }
  if (!validSource(projectUrl)) return result;
  try {
    const url = new URL(projectUrl);
    if (url.protocol !== 'https:' || !HOSTS.has(url.host) || url.username || url.password ||
        !/^\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+\/?$/.test(url.pathname) || url.search || url.hash) return result;
    url.pathname = url.pathname.replace(/\/?$/, '/');
    url.searchParams.set('q', `trace_id='${data.trace_id}'`);
    const time = Date.parse(data.created_at);
    if (typeof data.created_at === 'string' && /(?:Z|[+-]\d\d:\d\d)$/.test(data.created_at) && Number.isFinite(time)) {
      url.searchParams.set('since',new Date(time-3_600_000).toISOString());
      url.searchParams.set('until',new Date(time+3_600_000).toISOString());
    }
    return {...result,logfire_url:url.href,logfire_access:'account'};
  } catch { return result; }
}
