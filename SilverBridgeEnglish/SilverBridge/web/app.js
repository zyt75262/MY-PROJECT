/* UI only. All meal planning, validation and persistence run in Python.
 * This file never asks an AI model to generate a meal or a medical claim.
 */
(() => {
  'use strict';
  const labels = {"手机操作": "Phone help", "视频通话": "Video calls", "办事步骤": "Everyday tasks", "其他问题": "Other questions", "花生": "Peanut", "坚果": "Tree nuts", "蛋": "Egg", "奶": "Milk", "鱼": "Fish", "大豆": "Soy", "麸质": "Gluten", "主食": "Staple", "蛋白": "Protein", "果蔬": "Fruit & vegetables", "早": "Breakfast", "午": "Lunch", "晚": "Dinner", "全部": "All", "菜品": "Dishes", "粥": "Porridges", "汤": "Soups", "饮品": "Drinks", "羹": "Thick soups & puddings", "干果": "Nuts", "糕点": "Cakes", "其它": "Other", "想尝试": "Would try", "已经做过": "Made it", "不合口味": "Not for me"};
  const label = value => labels[value] || value;
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const money = cents => (cents / 100).toFixed(cents % 100 ? 2 : 0);
  const time = value => new Date(value).toLocaleString('en-US', {month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
  const state = {view:'home',error:''};
  let writes=0, polling=false;
  let data = {tickets:[],stories:[]};
  let recorder = null, recordingStream = null, recordingTimer = null;
  let draft = {image:null,audio:null,busy:false,recording:false,epoch:0};
  const paths = {
    leaf:'M18 3C7 2 2 6 4 13c2 7 12 7 14-10Z M4 20 15 8',
    grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    book:'M4 4h6c2 0 2 2 2 2s0-2 2-2h6v15h-6c-2 0-2 2-2 2s0-2-2-2H4z M12 6v15',
    heart:'M20.5 4.7a5 5 0 0 0-7 0L12 6.2l-1.5-1.5a5 5 0 0 0-7 7L12 20l8.5-8.3a5 5 0 0 0 0-7Z',
    help:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4 M12 16v.1',
    message:'M21 11a8 8 0 0 1-8 8H8l-5 3v-9a8 8 0 0 1 8-10h2a8 8 0 0 1 8 8Z M7 9h10 M7 13h7',
    home:'m3 10 9-7 9 7 M5 9v12h5v-7h4v7h5V9',
    check:'m5 12 4 4L19 6', arrow:'M4 12h15 m-5-5 5 5-5 5',
    swap:'M4 7h15m-4-4 4 4-4 4 M20 17H5m4-4-4 4 4 4',
    users:'M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z M2 21v-2a7 7 0 0 1 14 0v2 M17 4a4 4 0 0 1 0 7 M20 21v-2a7 7 0 0 0-3-6',
    mic:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0Z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8',
    image:'M3 3h18v18H3z m0 13 5-5 4 4 3-3 6 6 M15 7h.1',
    bowl:'M3 11h18c0 6-4 9-9 9s-9-3-9-9Z M7 3v4 M12 2v5 M17 3v4',
    sun:'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z M12 1v3 M12 20v3 M1 12h3 M20 12h3',
    download:'M12 3v12m-5-5 5 5 5-5 M4 16v5h16v-5', plus:'M12 4v16 M4 12h16'
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.leaf}"/></svg>`;
  const silverNav = [['home','home','Home'],['help','help','Ask for help'],['tickets','message','Help board'],['stories','book','Local stories'],['volunteer','users','Volunteer desk']];

  async function api(path, payload) {
    const options = payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Local-Request':'1'},body:JSON.stringify(payload)};
    let response;
    const controller = new AbortController(), timeout = setTimeout(()=>controller.abort(),12000);
    options.signal=controller.signal;
    try { response = await fetch(path, options); }
    catch (_) { throw new Error('Cannot connect to the Python server. Keep app.py running, then refresh this page.'); }
    finally { clearTimeout(timeout); }
    const result = await response.json();
    if (!response.ok) { const error=new Error(result.error || 'The action failed. Please try again.');error.status=response.status;throw error; }
    return result;
  }
  async function refresh() { data = await api('/api/state'); }
  function syncStatus(text) { const node=$('#syncstatus');if(node)node.textContent=text; }
  async function pollShared() {
    if(polling||writes||document.hidden||!['tickets','volunteer','stories'].includes(state.view))return;
    polling=true;
    try {
      const shared=await api('/api/shared');
      if(writes||$('#modal').open||[...document.querySelectorAll('audio')].some(node=>!node.paused))return;
      const changed=JSON.stringify([shared.tickets,shared.stories])!==JSON.stringify([data.tickets,data.stories]);
      data.tickets=shared.tickets;data.stories=shared.stories;
      if(changed&&!$('#modal').open&&!draft.recording&&!document.activeElement?.closest('audio'))render();
      syncStatus('Synced · '+new Date().toLocaleTimeString('en-US'));
    } catch(error) { syncStatus('Connection lost · Retrying'); }
    finally { polling=false; }
  }
  setInterval(pollShared,3000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)pollShared();});
  function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').classList.remove('show'), 4000); }
  function empty(title, text) { return `<div class="empty">${icon('leaf')}<h3>${title}</h3><p>${text}</p></div>`; }
  function stopRecording() {
    clearTimeout(recordingTimer);
    if (recorder?.state === 'recording') recorder.stop();
    recordingStream?.getTracks().forEach(track => track.stop()); recordingStream = null; draft.recording = false;
    const button = $('#recordbtn'); if (button) { button.classList.remove('recording'); button.innerHTML = icon('mic') + 'Record again'; }
  }
  function clearDraft() { draft.epoch++; stopRecording(); draft.image = null; draft.audio = null; draft.busy = false; }
  function navigate(view) { clearDraft(); state.view = view; state.error = ''; render(); window.scrollTo({top:0,behavior:'smooth'}); }
  function modal(title, html) { $('#modal').innerHTML = `<div class="modal-top"><h2>${esc(title)}</h2><button class="close" data-action="close" aria-label="Close">×</button></div><div class="modal-content">${html}</div>`; $('#modal').showModal(); }
  function closeModal() { if ($('#storyform')) clearDraft(); $('#modal').close(); }

  function render() {
    document.body.className = 'elder';
    $('#app').innerHTML = `<header class="topbar"><div class="brand"><div class="brandmark">${icon('leaf')}</div><span>SilverBridge</span></div><span class="statuspill">Standalone app · Python</span></header><div class="shell"><aside class="sidebar"><div class="appbrand"><strong>SilverBridge</strong><span>Community help</span></div><nav class="nav" aria-label="Application navigation">${silverNav.map(([view,name,label])=>`<button data-action="nav" data-view="${view}" title="${label}" class="${state.view===view?'active':''}" ${state.view===view?'aria-current="page"':''}>${icon(name)}<span>${label}</span></button>`).join('')}</nav><div class="side-note">Requests, screenshots, audio and replies are shared through this server.<p class="space">Records are stored in this application\'s own database.</p></div></aside><main class="main"><div class="breadcrumb"><span>SilverBridge</span><span id="syncstatus" role="status">Requests sync every 3 seconds</span></div>${silverContent()}<p class="bottom-note">Anyone who can connect can view and respond to requests. No personal accounts, emergency alerts or background notifications.</p></main></div>`;
  }

  function silverContent() {
    if(state.view==='home') return `<section class="hero"><div><div class="eyebrow">SILVER BRIDGE · Yinshanmen</div><h1>Phone problems?<br>Let us work through them together.</h1><p>Tell us where you got stuck.<br>A little patience can make the next step easier.</p><button class="btn" data-action="nav" data-view="help">${icon('help')}Ask for help ${icon('arrow')}</button></div></section><div class="quickgrid"><button class="quick" data-action="nav" data-view="help">${icon('mic')}<strong>Describe my problem</strong><p>Use text, audio or a screenshot</p></button><button class="quick" data-action="nav" data-view="tickets">${icon('message')}<strong>Check my progress</strong><p>Read replies and confirm a solution</p></button><button class="quick" data-action="nav" data-view="stories">${icon('book')}<strong>Share a local story</strong><p>Keep a memory in the community archive</p></button></div><div class="twocol"><div class="guide"><h3>First time? Follow these three steps</h3><ol><li>Choose Ask for help and describe or upload your problem.</li><li>A volunteer on another device opens Volunteer desk, claims the request and replies.</li><li>Read the synced reply on the Help board and confirm whether the problem is solved.</li></ol></div><div class="guide"><h3>One community across multiple devices</h3><p>Requests and stories remain after a restart. Other devices use the same server address to view requests and replies. Run the Python program on one computer only.</p></div></div>`;
    if(state.view==='help') return `<div class="result-head"><div><h1 style="font-size:34px">What do you need help with?</h1><p>Take your time. A short description is enough to begin.</p></div></div><div class="twocol"><section class="panel"><form id="helpform"><label class="label" for="helpcat">Choose a topic</label><select id="helpcat" name="category" class="control">${['手机操作','视频通话','办事步骤','其他问题'].map(value=>`<option value="${esc(value)}">${esc(label(value))}</option>`).join('')}</select><label class="label" for="helpbody">Describe what happened</label><textarea id="helpbody" name="body" class="control" maxlength="1200" placeholder="For example: I do not know how to start a video call with my family."></textarea><div class="attachment-form"><label class="filelabel">${icon('image')}Add a screenshot<input id="helpimage" type="file" accept="image/jpeg,image/png,image/webp"></label><label class="filelabel">${icon('mic')}Upload audio<input id="helpaudio" type="file" accept="audio/webm,audio/ogg,audio/wav,audio/mp4,audio/mpeg,audio/x-m4a"></label><button id="recordbtn" type="button" class="btn secondary" data-action="record">${icon('mic')}Record a message</button></div><p id="filestatus" class="small muted">Screenshots: up to 800 KB. Recordings: up to 45 seconds.</p><div id="audiopreview" class="draft-audio"></div><button type="submit" class="btn full space">Submit request ${icon('arrow')}</button></form></section><aside class="guide"><h3>Check before sharing</h3><p>Do not include identity numbers, verification codes or payment details. Anyone who can open this service can view shared requests and attachments.</p><p>Audio is kept as recorded. Phone browsers may block microphone access over local HTTP; upload an existing audio file instead.</p></aside></div>`;
    if(state.view==='stories') return `<div class="result-head"><div><div class="eyebrow muted">THE MEMORY OF OUR STREETS</div><h1 style="font-size:32px;margin-top:8px">Every street has a story.</h1><p>A familiar lane, an old shop, a memory worth keeping.</p></div><button class="btn" data-action="story">${icon('plus')}Share a story</button></div><div class="space">${data.stories.length?data.stories.map(story=>`<article class="story"><span class="eyebrow">Yinshanmen · A personal memory</span><h2>${esc(story.title)}</h2><p>${esc(story.body)}</p>${story.audio?`<audio controls src="${esc(story.audio)}"></audio>`:''}<div class="row"><span class="tag warm">Shared community story</span><span class="small muted">${time(story.created_at)}</span></div></article>`).join(''):empty('Be the first to share a memory','What was your favorite street like when you were young?')}</div><div class="notice">Submitted stories can be viewed by anyone who can connect. Obtain the storyteller\'s permission first.</div>`;
    const volunteer=state.view==='volunteer';
    return `<div class="result-head"><div><h1 style="font-size:32px">${volunteer?'A helping hand, one reply at a time.':'Help board'}</h1><p>${volunteer?'Volunteer workspace · Syncs every 3 seconds':'Look for new replies and confirm whether the problem is solved.'}</p></div><button class="btn secondary" data-action="refresh">Refresh</button></div>${volunteer?`<div class="stats">${[['pending','Waiting'],['active','In progress'],['done','Solved']].map(([status,label])=>`<div class="stat"><b>${data.tickets.filter(ticket=>ticket.status===status).length}</b><span>${label}</span></div>`).join('')}</div>`:''}<div class="space">${data.tickets.length?data.tickets.map(ticket=>ticketCard(ticket,volunteer)).join(''):empty('No requests yet','Requests submitted on another device will appear here automatically.')}</div>`;
  }
  function ticketCard(ticket,volunteer) { const labels={pending:'Waiting',active:'In progress',done:'Solved'};return `<article class="ticket"><header><span class="tag">${esc(label(ticket.category))}</span><span class="badge ${ticket.status}">${labels[ticket.status]}</span></header><p>${esc(ticket.body||(ticket.audio?'Please listen to my recorded question.':'Please look at my screenshot.'))}</p>${ticket.image?`<img class="attachment" src="${esc(ticket.image)}" alt="Screenshot attached to the request">`:''}${ticket.audio?`<audio controls preload="none" src="${esc(ticket.audio)}"></audio>`:''}${ticket.replies.map(reply=>`<div class="reply"><b>Volunteer reply · ${time(reply.created_at)}</b>${esc(reply.body).replace(/\n/g,'<br>')}</div>`).join('')}<footer><span>#${ticket.id} · ${time(ticket.created_at)}</span><div class="row">${volunteer&&ticket.status==='pending'?`<button class="btn" data-action="claim" data-id="${ticket.id}">I can help</button>`:''}${volunteer&&ticket.status==='active'?`<button class="btn" data-action="reply" data-id="${ticket.id}">Write a reply</button>`:''}${!volunteer&&ticket.status==='active'&&ticket.replies.length?`<button class="btn" data-action="resolve" data-id="${ticket.id}">Problem solved</button>`:''}${!volunteer&&ticket.status==='done'?`<button class="btn secondary" data-action="reopen" data-id="${ticket.id}">Still need help</button>`:''}</div></footer></article>`; }

  async function toggleRecording() {
    if(draft.recording){stopRecording();return;}
    if(draft.busy)throw new Error('Preparing the attachment. Please wait.');
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw new Error('This browser cannot record audio. Type a message or upload an audio file.');
    const epoch=draft.epoch; draft.busy=true;
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      if(epoch!==draft.epoch){stream.getTracks().forEach(track=>track.stop());return;}
      recordingStream=stream;const chunks=[];const active=new MediaRecorder(stream);recorder=active;draft.audio=null;
      active.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
      active.onstop=()=>{
        if(epoch!==draft.epoch)return;
        draft.busy=true;const blob=new Blob(chunks,{type:active.mimeType||'audio/webm'});
        if(blob.size>1200000){draft.busy=false;toast('The recording is too large. Please record a shorter message.');return;}
        const reader=new FileReader();reader.onload=()=>{if(epoch!==draft.epoch)return;draft.audio=reader.result;draft.busy=false;if($('#audiopreview'))$('#audiopreview').innerHTML=`<audio controls src="${esc(draft.audio)}"></audio><p class="small muted">Audio is ready. Submit the form to save it.</p>`;};reader.onerror=()=>{draft.busy=false;toast('Could not read the audio. Please try again.');};reader.readAsDataURL(blob);
      };
      active.start();draft.recording=true;draft.busy=false;$('#recordbtn').classList.add('recording');$('#recordbtn').innerHTML=icon('mic')+'Recording · Click to stop';recordingTimer=setTimeout(stopRecording,45000);
    } catch(error) { recordingStream?.getTracks().forEach(track=>track.stop());draft.busy=false;throw new Error('Could not start recording. Check microphone permissions, type a message or upload audio.'); }
  }

  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-action]');if(!button||button.disabled)return;
    const action=button.dataset.action;button.disabled=true;writes++;
    try {
      if(action==='nav'){await refresh();navigate(button.dataset.view);}
      else if(action==='refresh'){await refresh();render();toast('Records refreshed');}
      else if(action==='close')closeModal();
      else if(action==='record')await toggleRecording();
      else if(['claim','resolve','reopen'].includes(action)){await api(`/api/tickets/${button.dataset.id}/${action}`,{});await refresh();render();toast('Request status updated');}
      else if(action==='reply'){modal('Explain one step at a time',`<form id="replyform" data-id="${button.dataset.id}"><label class="label" for="replybody">Your reply</label><textarea id="replybody" name="body" class="control" maxlength="1600" required placeholder="First, open the conversation with your family member..."></textarea><button type="submit" class="btn full space">Save reply</button></form>`);}
      else if(action==='story'){clearDraft();modal('Keep a local memory',`<form id="storyform"><label class="label" for="storytitle">Story title</label><input id="storytitle" name="title" class="control" maxlength="60" required placeholder="For example: The old shop on the corner"><label class="label" for="storybody">Tell your story</label><textarea id="storybody" name="body" class="control" maxlength="4000" placeholder="When I was young..."></textarea><button type="button" id="recordbtn" class="btn secondary space" data-action="record">${icon('mic')}Record a story</button><div id="audiopreview" class="draft-audio"></div><label class="space"><input type="checkbox" name="share" required> I have the storyteller\'s permission to share this story with people using this service.</label><button type="submit" class="btn full space">Share with the community</button></form>`);}
    } catch(error){toast(error.message);}finally{button.disabled=false;writes--;}
  });
  document.addEventListener('change',event=>{
    if(event.target.id==='helpaudio'){
      const file=event.target.files[0];if(!file)return;
      const types={'audio/x-m4a':'audio/mp4','audio/x-wav':'audio/wav'};
      const mime=types[file.type]||file.type;
      if(!['audio/webm','audio/ogg','audio/wav','audio/mp4','audio/mpeg'].includes(mime)||file.size>1200000){event.target.value='';toast('Choose an audio file no larger than 1.2 MB.');return;}
      const epoch=draft.epoch;draft.busy=true;const reader=new FileReader();reader.onload=()=>{if(epoch!==draft.epoch)return;draft.audio=reader.result.replace(/^data:[^;]+;/,'data:'+mime+';');draft.busy=false;$('#audiopreview').innerHTML=`<audio controls src="${esc(draft.audio)}"></audio>`;};reader.onerror=()=>{draft.busy=false;toast('Could not read the audio');};reader.readAsDataURL(file);
    }
    if(event.target.id==='helpimage'){
      const file=event.target.files[0];if(!file)return;
      if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>800000){event.target.value='';draft.image=null;toast('Choose a PNG, JPEG or WebP image no larger than 800 KB.');return;}
      const epoch=draft.epoch;draft.busy=true;const reader=new FileReader();reader.onload=()=>{if(epoch!==draft.epoch)return;draft.image=reader.result;draft.busy=false;if($('#filestatus'))$('#filestatus').textContent='Screenshot ready: '+file.name;};reader.onerror=()=>{draft.busy=false;toast('Could not read the image. Please try again.');};reader.readAsDataURL(file);
    }
  });
  document.addEventListener('submit',async event=>{
    event.preventDefault();const form=event.target,fields=new FormData(form),button=form.querySelector('button[type=submit]');
    if(button?.disabled)return;if(button)button.disabled=true;writes++;
    try {
      if(form.id==='helpform'){if(draft.recording||draft.busy)throw new Error('Stop recording and wait for attachments to finish loading.');await api('/api/tickets',{category:fields.get('category'),body:fields.get('body'),image:draft.image,audio:draft.audio});await refresh();navigate('tickets');toast('Request shared. Volunteers on other devices can now respond.');}
      else if(form.id==='replyform'){await api(`/api/tickets/${form.dataset.id}/reply`,{body:fields.get('body')});await refresh();closeModal();render();toast('Reply saved');}
      else if(form.id==='storyform'){if(draft.recording||draft.busy)throw new Error('Stop recording and wait for attachments to finish loading.');await api('/api/stories',{title:fields.get('title'),body:fields.get('body'),audio:draft.audio,share:fields.get('share')==='on'});await refresh();closeModal();render();toast('Story shared with the community');}
    } catch(error){toast(error.message);}finally{if(button)button.disabled=false;writes--;}
  });
  $('#modal').addEventListener('cancel',()=>{if($('#storyform'))clearDraft();});
  window.addEventListener('beforeunload',stopRecording);
  refresh().then(render).catch(error=>{$('#app').innerHTML=`<div class="loading"><h1>Local server not connected</h1><p>${esc(error.message)}</p><p>In the project folder, run <code>python app.py</code>，then open the address shown in the startup window.</p></div>`;});
})();
