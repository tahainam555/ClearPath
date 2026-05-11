// Frontend SocketIO client + UI interactions for ObstacleAware
(function(){
  const socket = io();
  const img = document.getElementById('depthView');
  const zoneLeft = document.getElementById('zone-left');
  const zoneCentre = document.getElementById('zone-centre');
  const zoneRight = document.getElementById('zone-right');
  const status = document.getElementById('status');
  const muteBtn = document.getElementById('muteBtn');
  const slider = document.getElementById('sensitivity');

  let muted = false;
  let lastSpoken = 0;
  const COOLDOWN_MS = 3000;

  muteBtn.addEventListener('click', ()=>{
    muted = !muted;
    muteBtn.textContent = muted ? 'Unmute' : 'Mute';
  });

  slider.addEventListener('change', ()=>{
    const val = slider.value;
    fetch('/settings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({threshold: Number(val)})})
      .then(r=>r.json()).then(j=>{
        if(j.status==='ok'){
          status.textContent = `Sensitivity set to ${j.threshold}`;
        }
      }).catch(()=>{
        status.textContent = 'Error updating sensitivity';
      });
  });

  socket.on('connect', ()=>{
    status.textContent = 'Connected';
  });

  socket.on('disconnect', ()=>{
    status.textContent = 'Disconnected';
  });

  socket.on('frame', (data)=>{
    if(data && data.image){
      img.src = data.image;
    }
  });

  socket.on('zones', (zones)=>{
    if(!zones) return;
    // update classes
    zoneLeft.classList.toggle('danger', !!zones.left.danger);
    zoneLeft.classList.toggle('clear', !zones.left.danger);
    zoneCentre.classList.toggle('danger', !!zones.centre.danger);
    zoneCentre.classList.toggle('clear', !zones.centre.danger);
    zoneRight.classList.toggle('danger', !!zones.right.danger);
    zoneRight.classList.toggle('clear', !zones.right.danger);
  });

  socket.on('alert', (data)=>{
    const msg = data && data.message ? data.message : null;
    status.textContent = msg ? msg : 'All clear';
    if(msg && !muted){
      const now = Date.now();
      if(now - lastSpoken > COOLDOWN_MS){
        lastSpoken = now;
        try{
          const u = new SpeechSynthesisUtterance(msg);
          window.speechSynthesis.speak(u);
        }catch(e){
          console.warn('Speech synthesis failed', e);
        }
      }
    }
  });

  // graceful error display
  socket.on('connect_error', (err)=>{
    status.textContent = 'Connection error';
  });

})();
