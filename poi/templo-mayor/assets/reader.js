(() => {
  'use strict';

  const modeLinks = Array.from(document.querySelectorAll('.reader-nav a'));
  const panels = Array.from(document.querySelectorAll('[data-reader-panel]'));
  const history = document.getElementById('history');
  const explore = document.getElementById('explore');
  const stops = Array.from(explore.querySelectorAll('[data-stop]'));
  const jump = document.getElementById('choose-stop');
  const previous = document.getElementById('previous-stop');
  const next = document.getElementById('next-stop');
  const progress = document.getElementById('stop-progress');
  let activeStop = 0;
  let focusStop = false;

  for (const stop of stops) {
    const title = stop.querySelector('h3');
    jump.add(new Option(title.textContent, stop.id));
    title.tabIndex = -1;
  }
  jump.closest('.stop-select').hidden = false;
  next.closest('.stop-pager').hidden = false;

  function goToStop(stop) {
    if (!stop) return;
    focusStop = true;
    // Safari does not dispatch hashchange when the user reselects the active
    // stop. Restore focus and scroll explicitly rather than leaving stale state.
    if (location.hash === '#' + stop.id) navigateHash();
    else location.hash = stop.id;
  }

  jump.addEventListener('change', () => goToStop(document.getElementById(jump.value)));
  previous.addEventListener('click', () => goToStop(stops[activeStop - 1]));
  next.addEventListener('click', () => goToStop(stops[activeStop + 1]));

  function navigateHash() {
    let fragment = location.hash.slice(1);
    try {
      fragment = decodeURIComponent(fragment);
    } catch {
      // A malformed fragment still opens the default history.
    }
    const target = document.getElementById(fragment);
    const panel = target?.closest('[data-reader-panel]') ?? history;
    const stop = target?.closest('[data-stop]');
    activeStop = stop ? stops.indexOf(stop) : 0;

    for (const item of panels) item.hidden = item !== panel;
    for (const link of modeLinks) {
      if (link.hash === '#' + panel.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }

    stops.forEach((item, index) => { item.hidden = index !== activeStop; });
    jump.value = stops[activeStop].id;
    previous.disabled = activeStop === 0;
    next.disabled = activeStop === stops.length - 1;
    progress.textContent = `Stop ${activeStop + 1} of ${stops.length}`;

    if (focusStop) stops[activeStop].querySelector('h3').focus({ preventScroll: true });
    focusStop = false;
    if (target) {
      // Alias spans from older URLs are empty. Scroll to the visible section.
      const destination = stop || target.closest('details') || (target.tagName === 'SPAN' ? panel : target);
      if (destination instanceof HTMLDetailsElement) destination.open = true;
      requestAnimationFrame(() => destination.scrollIntoView({ block: 'start' }));
    }
  }

  navigateHash();
  window.addEventListener('hashchange', navigateHash);
})();
