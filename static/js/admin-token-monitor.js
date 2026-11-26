(() => {
  const root = document.getElementById('token-monitor');
  if (!root) return;
  const button = document.getElementById('token-refresh');
  const state = document.getElementById('token-state');
  const fmt = value => Number.isFinite(value) ? value.toLocaleString('es-AR') : '—';
  const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
  const routeName = row => {const el = node('td', row.provider.toUpperCase());el.append(node('span', row.model, 'token-model-name'));return el;};
  function rows(id, data, create) {const body=document.getElementById(id);body.replaceChildren();if (!data.length) {const cell=node('td','Todavía no hay datos registrados.');cell.colSpan=7;const row=node('tr');row.append(cell);body.append(row);} else data.forEach(item=>body.append(create(item)));}
  function meter(value, limit) {const cell=node('td', limit ? `${fmt(value)} / ${fmt(limit)}` : '—');if(limit){const bar=document.createElement('meter');bar.min=0;bar.max=limit;bar.value=Math.min(limit,Math.max(0,value));bar.style.display='block';bar.setAttribute('aria-label', `${fmt(value)} de ${fmt(limit)}`);cell.append(bar);}return cell;}
  let busy=false;
  async function refresh() {
    if (busy || document.hidden) return;
    busy=true;button.disabled=true;
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),10000);
    try {
      const response=await fetch(root.dataset.url,{credentials:'same-origin',signal:controller.signal,cache:'no-store'});
      if (!response.ok || response.redirected) throw new Error('unavailable');
      const data=await response.json();const total=data.totals;
      document.getElementById('tokens-total').textContent=fmt(total.total_tokens);
      document.getElementById('tokens-input').textContent=fmt(total.prompt_tokens);
      document.getElementById('tokens-output').textContent=fmt(total.completion_tokens);
      document.getElementById('tokens-requests').textContent=`${fmt(total.requests)} / ${fmt(total.errors)}`;
      document.getElementById('tokens-coverage').textContent=`${fmt(total.usage_responses)} llamadas con datos de uso · ${fmt(total.rate_limited)} respuestas 429`;
      rows('token-models',data.models,item=>{const row=node('tr');row.append(routeName(item));['prompt_tokens','completion_tokens','total_tokens','requests','errors','usage_responses'].forEach(field=>row.append(node('td',fmt(item[field]))));return row;});
      rows('token-routes',data.routes,item=>{const row=node('tr');const name=routeName(item);name.append(node('small',`Ruta ${item.slot}`));row.append(name,meter(item.requests_minute,item.requests_minute_limit),meter(item.input_tokens_minute,item.input_tokens_minute_limit),meter(item.requests_day,item.requests_day_limit));row.append(node('td',item.reported_remaining_tokens==null?'Sin dato vigente':`${fmt(item.reported_remaining_tokens)} tokens · reinicio ~${fmt(item.reported_reset_seconds)} s`));row.append(node('td',item.cooldown_seconds>0?`Esperando ~${fmt(item.cooldown_seconds)} s`:'Sin pausa local'));return row;});
      const chart=document.getElementById('token-chart');chart.replaceChildren();const max=Math.max(1,...data.hours.map(hour=>hour.total_tokens));
      data.hours.forEach((hour,index)=>{const date=new Date(hour.at);const label=date.toLocaleString('es-AR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});const col=node('div',undefined,'token-hour');const bar=node('span',undefined,'token-bar');bar.style.height=`${hour.total_tokens/max*100}%`;col.title=`${label}: ${fmt(hour.total_tokens)} tokens`;col.setAttribute('role','img');col.setAttribute('aria-label',col.title);col.append(bar);if(index%3===0)col.append(node('small',date.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})));chart.append(col);});
      document.getElementById('token-started').textContent=data.started_at?`Registro iniciado: ${new Date(Number(data.started_at)*1000).toLocaleString('es-AR')}.`:'El registro está activo. Todavía no se observaron nuevas llamadas a los proveedores.';
      state.textContent=`Última actualización: ${new Date(data.generated_at).toLocaleTimeString('es-AR')} · Vercel ${data.vercel_enabled?'activado':'desactivado'}`;state.className='';
    } catch (_) {state.textContent='No se pudo actualizar el consumo. Los datos visibles pueden estar desactualizados; se reintentará automáticamente.';state.className='token-error';}
    finally {clearTimeout(timeout);busy=false;button.disabled=false;}
  }
  button.addEventListener('click',refresh);refresh();setInterval(refresh,15000);
})();
