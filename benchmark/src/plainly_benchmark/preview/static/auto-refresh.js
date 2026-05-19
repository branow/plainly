(async () => {
  let last = null;
  while (true) {
    try {
      const r = await fetch('/api/state', { cache: 'no-store' });
      const j = await r.json();
      if (last !== null && j.mtime !== last) {
        location.reload();
        return;
      }
      last = j.mtime;
    } catch (e) {
      /* ignore */
    }
    await new Promise(r => setTimeout(r, 2000));
  }
})();
