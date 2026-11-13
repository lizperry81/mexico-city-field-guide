(() => {
  'use strict';

  const modeLinks = Array.from(document.querySelectorAll('.reader-nav a'));
  const sectionLinks = Array.from(document.querySelectorAll('.history-chapters a[href^="#"]'));
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
  let focusMode = false;
  let focusSection = false;

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

  // Clicking a mode moves keyboard and VoiceOver focus to its visible heading.
  // Deep links and browser Back/Forward keep their existing focus behavior.
  for (const link of modeLinks) {
    link.addEventListener('click', () => {
      focusMode = true;
      // Safari does not emit hashchange when the active mode is selected again.
      if (location.hash === link.hash) navigateHash();
    });
  }

  // A table-of-contents activation should identify the newly visible section
  // to keyboard and screen-reader users. Browser history/deep links must not
  // move focus without a deliberate reader action.
  for (const link of sectionLinks) {
    link.addEventListener('click', () => {
      focusSection = true;
      // iOS Safari does not fire hashchange when the same link is tapped again.
      if (location.hash === link.hash) navigateHash();
    });
  }

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
    // Switching to Discover or Plan must not discard a visitor's position
    // in the guided walk. A direct link to a different stop still takes priority.
    // On an initial visit activeStop starts at the first stop.
    if (stop) activeStop = stops.indexOf(stop);

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

    if (focusMode) {
      const heading = panel.querySelector('h2');
      if (heading) {
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
      }
    }
    focusMode = false;
    if (focusSection && panel === history && target &&
        sectionLinks.some(link => link.hash === '#' + target.id)) {
      const heading = target.querySelector('h3');
      if (heading) {
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
      }
    }
    focusSection = false;
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
