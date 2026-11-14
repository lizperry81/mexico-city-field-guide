#!/usr/bin/env node
// No browser dependency: emulate hashchange semantics Safari uses for same-anchor navigation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync(process.argv[2] || 'site/poi/templo-mayor/assets/reader.js', 'utf8');
const listeners = {};
const panels = Object.fromEntries(['history', 'explore', 'plan'].map(id => [
  id, {id, hidden: false, scrollIntoView() {}, closest(selector) {
    return selector === '[data-reader-panel]' ? this : null;
  }}
]));
for (const panel of Object.values(panels)) {
  const heading = {focused: 0, focus() {this.focused += 1;}};
  panel.heading = heading;
  panel.querySelector = selector => {assert.equal(selector, 'h2'); return heading;};
}
const photoHrefOverrides = new Map();
const stops = ['plaza', 'twin-stairs', 'older-stairs'].map(id => {
  const heading = {textContent: id, focused: 0, focus() {this.focused += 1;}};
  return {
    id, hidden: false, heading, tagName: 'SECTION', scrolled: 0,
    querySelector(selector) {
      if (selector === 'h3') return heading;
      if (selector === '.field-photo') return photoFigures[id + '-reference-photo'];
      if (selector === '.field-photo img') return {
        getAttribute(key) {
          if (key === 'src') return 'assets/' + id + '.webp';
          if (key === 'alt') return 'Identifiable features at ' + id;
          return null;
        }
      };
      if (selector === '.photo-zoom') return {
        getAttribute(key) {return key === 'href' ? (photoHrefOverrides.get(id) || 'assets/' + id + '.webp') : null;}
      };
      throw Error('Unexpected stop selector: ' + selector);
    },
    closest(selector) {
      if (selector === '[data-reader-panel]') return panels.explore;
      if (selector === '[data-stop]') return this;
      return null;
    },
    scrollIntoView() {this.scrolled += 1;}
  };
});
const photoFigures = Object.fromEntries(stops.map(stop => {
  const id = stop.id + '-reference-photo';
  return [id, {
    id, tagName: 'FIGURE', focused: 0, scrolled: 0,
    classList: {contains(name) {return name === 'field-photo';}},
    focus() {this.focused += 1;},
    scrollIntoView() {this.scrolled += 1;},
    closest(selector) {
      if (selector === '[data-reader-panel]') return panels.explore;
      if (selector === '[data-stop]') return stop;
      return null;
    }
  }];
}));
const sections = ['dossier-topic-1', 'dossier-topic-2'].map(id => {
  const heading = {focused: 0, focus() {this.focused += 1;}};
  return {
    id, heading, scrolled: 0, tagName: 'SECTION',
    querySelector(selector) {assert.equal(selector, 'h3'); return heading;},
    closest(selector) {
      return selector === '[data-reader-panel]' ? panels.history : null;
    },
    scrollIntoView() {this.scrolled += 1;}
  };
});
const sectionLinks = sections.map(section => ({
  hash: '#' + section.id, click: null,
  addEventListener(type, fn) {assert.equal(type, 'click'); this.click = fn;}
}));
const returnLinks = [{
  hash: '#history-contents', click: null,
  addEventListener(type, fn) {assert.equal(type, 'click'); this.click = fn;}
}];
const historyContents = {
  id: 'history-contents', tagName: 'NAV', focused: 0, scrolled: 0,
  focus() {this.focused += 1;},
  closest(selector) {
    return selector === '[data-reader-panel]' ? panels.history : null;
  },
  scrollIntoView() {this.scrolled += 1;}
};
const skip = {
  click: null,
  addEventListener(type, fn) {assert.equal(type, 'click'); this.click = fn;}
};
const links = Object.keys(panels).map(id => ({
  hash: '#' + id, current: false, click: null,
  addEventListener(type, fn) {assert.equal(type, 'click'); this.click = fn;},
  setAttribute(name) {assert.equal(name, 'aria-current'); this.current = true;},
  removeAttribute(name) {assert.equal(name, 'aria-current'); this.current = false;}
}));
const jump = {
  options: [], value: '', listener: null,
  add(option) {this.options.push(option);},
  closest() {return {hidden: false};},
  addEventListener(type, fn) {assert.equal(type, 'change'); this.listener = fn;}
};
function button() {
  return {
    disabled: false, listener: null,
    closest() {return {hidden: false};},
    addEventListener(type, fn) {assert.equal(type, 'click'); this.listener = fn;}
  };
}
const prev = button(), next = button(), progress = {textContent: ''};
const stopPosition = {textContent: ''};
const reference = {hidden: true};
const referenceThumb = {src: ''};
const referenceDescription = {textContent: ''};
const referenceCaption = {
  href: '', click: null,
  get hash() {return this.href;},
  addEventListener(type, fn) {assert.equal(type, 'click'); this.click = fn;}
};
const referenceLink = {
  href: '', ariaLabel: '',
  setAttribute(name, value) {assert.equal(name, 'aria-label'); this.ariaLabel = value;}
};
const ids = {...panels, ...photoFigures, ...Object.fromEntries(stops.map(stop => [stop.id, stop])),
  ...Object.fromEntries(sections.map(section => [section.id, section])),
  'choose-stop': jump, 'previous-stop': prev, 'next-stop': next,
  'skip-to-history': skip, 'history-contents': historyContents,
  'stop-progress': progress, 'stop-position': stopPosition,
  'stop-reference': reference, 'stop-reference-link': referenceLink,
  'stop-reference-thumb': referenceThumb,
  'stop-reference-description': referenceDescription,
  'stop-reference-caption': referenceCaption};
const doc = {
  querySelectorAll(selector) {
    if (selector === '.reader-nav a') return links;
    if (selector === '.history-chapters a[href^="#"]') return sectionLinks;
    if (selector === '.return-to-contents a[href="#history-contents"]') return returnLinks;
    if (selector === '[data-reader-panel]') return Object.values(panels);
    throw new Error('Unexpected document query: ' + selector);
  },
  getElementById(id) {return ids[id] || null;}
};
panels.explore.querySelectorAll = selector => {
  assert.equal(selector, '[data-stop]'); return stops;
};
const location = {
  _hash: '#plaza',
  get hash() {return this._hash;},
  set hash(fragment) {
    const normalized = fragment.startsWith('#') ? fragment : '#' + fragment;
    // Browsers (including iOS Safari) do NOT fire hashchange on same-hash assignment.
    if (this._hash === normalized) return;
    this._hash = normalized;
    listeners.hashchange?.();
  }
};
const store = new Map();
const storage = {
  getItem(key) {return store.get(key) ?? null;},
  setItem(key, value) {store.set(key, value);}
};
const windowContext = {sessionStorage: storage,
  addEventListener(type, fn) {listeners[type] = fn;}};
const sandbox = {
  document: doc, window: windowContext, location,
  Option: function(label, value) {return {label, value};},
  requestAnimationFrame(fn) {fn();}, HTMLDetailsElement: class {}
};
vm.runInNewContext(code, {...sandbox});
assert.equal(progress.textContent, 'Stop 1 of 3');
assert.equal(stopPosition.textContent, progress.textContent, 'Current stop must be visible near the picker');
assert.equal(jump.value, 'plaza');
assert.equal(reference.hidden, false);
assert.equal(referenceThumb.src, 'assets/plaza.webp');
assert.equal(referenceLink.href, 'assets/plaza.webp');
assert.equal(referenceDescription.textContent, 'Identifiable features at plaza');
assert.equal(referenceCaption.href, '#plaza-reference-photo');
assert.equal(prev.disabled, true);
assert.equal(next.disabled, false);
jump.listener(); // Safari no hashchange when reselecting current stop.
assert.equal(stops[0].heading.focused, 1, 'Same-stop activation must restore focus');
assert.equal(stops[0].scrolled, 2, 'Same-stop activation must scroll to the active stop');
jump.value = 'twin-stairs';
jump.listener();
assert.equal(location.hash, '#twin-stairs');
assert.equal(progress.textContent, 'Stop 2 of 3');
assert.equal(stopPosition.textContent, progress.textContent, 'Stop picker must follow walk navigation');
assert.equal(referenceThumb.src, 'assets/twin-stairs.webp', 'Preview must follow the active walk stop');
assert.equal(referenceLink.href, 'assets/twin-stairs.webp', 'Enlargement must match the active stop');
assert.match(referenceLink.ariaLabel, /twin-stairs/);
assert.equal(stops[1].heading.focused, 1);
assert.equal(prev.disabled, false);
location.hash = '#history'; // Back/forward or history tab.
assert.equal(panels.history.hidden, false);
assert.equal(panels.explore.hidden, true);
// Reading historical context or planning a visit should preserve the active
// on-site stop, so visitors can return to the same physical observation.
location.hash = '#explore';
assert.equal(jump.value, 'twin-stairs', 'Explore must resume the last visited stop');
assert.equal(progress.textContent, 'Stop 2 of 3');
assert.equal(stops[1].hidden, false, 'The last selected stop should be visible');
assert.equal(prev.disabled, false);
location.hash = '#plan';
assert.equal(panels.plan.hidden, false);
location.hash = '#explore';
assert.equal(jump.value, 'twin-stairs', 'Plan must not reset the Explore walk');
location.hash = '#plaza'; // An explicit stop deep link overrides resumed progress.
assert.equal(panels.explore.hidden, false);
assert.equal(jump.value, 'plaza');
assert.equal(progress.textContent, 'Stop 1 of 3');
assert.equal(panels.history.heading.focused, 0, 'Back/Forward must not steal heading focus');
const historyLink = links.find(link => link.hash === '#history');
historyLink.click();
location.hash = '#history';
assert.equal(panels.history.heading.focused, 1, 'Choosing Discover should focus its heading');
assert.equal(panels.history.heading.tabIndex, -1);
historyLink.click(); // No hashchange on repeated Discover tap in Safari.
assert.equal(panels.history.heading.focused, 2, 'Repeated mode tap should refocus the visible heading');
// A keyboard skip focuses the article even with an unchanged Safari hash.
const skipBefore = panels.history.heading.focused;
skip.click();
assert.equal(panels.history.heading.focused, skipBefore + 1);
const planLink = links.find(link => link.hash === '#plan');
planLink.click();
location.hash = '#plan';
assert.equal(panels.plan.heading.focused, 1, 'Choosing Plan should focus its heading');
assert.equal(panels.explore.hidden, true);
const focusBeforeSkip = panels.history.heading.focused;
skip.click();
location.hash = '#history';
assert.equal(panels.history.heading.focused, focusBeforeSkip + 1);
location.hash = '#explore'; // History navigation does not trigger tab-click focus.
assert.equal(panels.explore.heading.focused, 0);
const exploreLink = links.find(link => link.hash === '#explore');
exploreLink.click(); // The current Explore mode can be tapped again.
assert.equal(panels.explore.heading.focused, 1);
assert.equal(stops[0].heading.focused, 1, 'Mode navigation must not alter stop selection');
// The Discover contents links must handle the same-hash Safari case while
// keeping ordinary direct links and browser Back/Forward free of focus jumps.
sectionLinks[0].click();
location.hash = '#dossier-topic-1';
assert.equal(panels.history.hidden, false);
assert.equal(sections[0].heading.focused, 1);
assert.equal(sections[0].heading.tabIndex, -1);
assert.equal(sections[0].scrolled, 1);
sectionLinks[0].click(); // Same article heading: no hashchange event.
assert.equal(sections[0].heading.focused, 2);
assert.equal(sections[0].scrolled, 2);
location.hash = '#dossier-topic-2'; // Direct/history navigation must not steal focus.
assert.equal(sections[1].heading.focused, 0);
assert.equal(sections[1].scrolled, 1);
// Return links restore focus to the contents, including same-hash Safari taps.
// They must leave the on-site walk's selected stop and URL behavior intact.
returnLinks[0].click();
location.hash = '#history-contents';
assert.equal(panels.history.hidden, false, 'Return link must show the history panel');
assert.equal(historyContents.focused, 1, 'Return must focus the historical contents');
assert.equal(historyContents.scrolled, 1, 'Return must scroll to the contents');
returnLinks[0].click();
assert.equal(historyContents.focused, 2, 'Repeated Safari return must restore focus');
assert.equal(historyContents.scrolled, 2, 'Repeated return must scroll to the contents');
location.hash = '#explore';
assert.equal(jump.value, 'plaza', 'Discover return must not reset the physical walk');
// A reload in the same tab should restore the selected on-site stop without
// touching the annotation system's independent localStorage.
const key = 'cdmx:templo-mayor:explore-stop';
assert.equal(store.get(key), 'plaza');
store.set(key, 'older-stairs');
location._hash = '#explore';
vm.runInNewContext(code, {...sandbox}); // A fresh JS context simulates reload.
assert.equal(jump.value, 'older-stairs', 'Explore reload must resume a stored stop');
assert.equal(stopPosition.textContent, 'Stop 3 of 3', 'Reloaded walk must show saved position');
assert.equal(progress.textContent, 'Stop 3 of 3');
assert.equal(stops[2].hidden, false);
location._hash = '#plaza';
vm.runInNewContext(code, {...sandbox});
assert.equal(jump.value, 'plaza', 'An explicit deep link overrides saved progress');
assert.equal(store.get(key), 'plaza', 'An explicit stop updates the saved progress');
// Storage can be disabled under Safari privacy restrictions.
location._hash = '#twin-stairs';
const blockedWindow = {...windowContext, sessionStorage: {
  getItem() {throw new Error('Storage unavailable');},
  setItem() {throw new Error('Storage unavailable');}
}};
vm.runInNewContext(code, {...sandbox, window: blockedWindow});
assert.equal(jump.value, 'twin-stairs', 'Navigation still works without storage');
assert.equal(stopPosition.textContent, 'Stop 2 of 3', 'Position must work with storage disabled');
// An editorial image mismatch must not show the wrong picture as a field guide.
photoHrefOverrides.set('plaza', 'assets/unrelated-photo.webp');
location.hash = '#plaza';
assert.equal(reference.hidden, true, 'Mismatched enlarged image must suppress the preview');
photoHrefOverrides.delete('plaza');
location.hash = '#twin-stairs';
location.hash = '#plaza';
assert.equal(reference.hidden, false, 'A corrected, matching photo restores the preview');
assert.equal(referenceThumb.src, referenceLink.href, 'Preview and enlargement must match');
// The on-site preview must link back to its credited figure, not strand the
// reader on a bare image URL. Figure anchors preserve markers and captions.
location.hash = '#twin-stairs';
assert.equal(referenceCaption.href, '#twin-stairs-reference-photo');
const figure = photoFigures['twin-stairs-reference-photo'];
referenceCaption.click();
location.hash = referenceCaption.href;
assert.equal(figure.focused, 1, 'Photo shortcut should focus the original figure');
assert.equal(figure.scrolled, 1, 'Photo shortcut should scroll to the captioned figure');
assert.equal(jump.value, 'twin-stairs', 'Photo shortcut must preserve the active stop');
referenceCaption.click(); // Safari does not fire hashchange for same hash.
assert.equal(figure.focused, 2, 'Repeat Safari taps must refocus the figure');
assert.equal(figure.scrolled, 2, 'Repeat Safari taps must scroll back to the figure');
location.hash = '#history';
location.hash = referenceCaption.href;
assert.equal(jump.value, 'twin-stairs', 'Deep links to figures should reopen the right Explore stop');
console.log('PASS: Discover/Explore navigation, credited photo-caption anchors, Safari focus, pager, stop resume, deep links, and blocked storage');
