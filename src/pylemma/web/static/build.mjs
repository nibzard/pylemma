/** Poll a durable reference; never repeat a provider request automatically. */
export const BUILD_STAGES = {
  connecting:'Connecting to the server',
  starting:'Starting the server',
  generating:'Building your player',
  checking:'Testing its rules',
  saving:'Saving your player',
  finishing:'Finishing the build',
  complete:'Your player is saved',
};
export async function buildPlayer(body, {
  requestId, onStage=()=>{}, fetcher=fetch, start=true,
  delay=ms=>new Promise(resolve=>setTimeout(resolve,ms)), now=Date.now,
  timeoutMs=180000,
}) {
  const controller=new AbortController();
  let completed, rejected;
  const failure=(text, recoverable=true)=>{
    const error=new Error(text+' Reference: '+requestId);
    error.recoverable=recoverable;
    return error;
  };
  onStage('connecting');
  if (start) {
    // The original response and status polling can independently deliver completion.
    void fetcher('/api/machines',{
      method:'POST',headers:{'Content-Type':'application/json','X-Request-ID':requestId},
      body:JSON.stringify(body),signal:controller.signal,
    }).then(async response=>{
      const data=await response.json();
      if (response.ok && data.machine) completed=data;
      else if (!response.ok && response.status < 500) {
        rejected=failure(data.detail || 'The build was rejected.',false);
      }
    }).catch(()=>{ /* Status polling resolves an uncertain transport outcome. */ });
  }
  const deadline=now()+timeoutMs;
  const timeout=setTimeout(()=>controller.abort(),timeoutMs);
  try {
    while (now() < deadline) {
      if (completed) { onStage('complete'); return completed; }
      if (rejected) throw rejected;
      let data;
      try {
        const response=await fetcher('/api/builds/'+encodeURIComponent(requestId),{
          cache:'no-store',signal:controller.signal,
        });
        if (response.ok) data=await response.json();
      } catch { /* Keep the reference. Never regenerate to repair a lost response. */ }
      if (data?.stage === 'complete' && data.machine) {
        onStage('complete');
        return {machine:data.machine};
      }
      if (data?.stage === 'failed') throw failure(data.detail,false);
      if (data?.stage === 'interrupted') throw failure(data.detail);
      if (BUILD_STAGES[data?.stage]) onStage(data.stage);
      await delay(1000);
    }
    throw failure('The build is not confirmed yet. Your description and reference are saved. Check this build again.');
  } finally { clearTimeout(timeout); controller.abort(); }
}
