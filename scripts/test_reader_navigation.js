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
const stops = ['plaza', 'twin-stairs', 'older-stairs'].map(id => {
  const heading = {textContent: id, focused: 0, focus() {this.focused += 1;}};
  return {
    id, hidden: false, heading, tagName: 'SECTION', scrolled: 0,
    querySelector(selector) {assert.equal(selector, 'h3'); return heading;},
    closest(selector) {
      if (selector === '[data-reader-panel]') return panels.explore;
      if (selector === '[data-stop]') return this;
      return null;
    },
    scrollIntoView() {this.scrolled += 1;}
  };
});
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
const ids = {...panels, ...Object.fromEntries(stops.map(stop => [stop.id, stop])),
  ...Object.fromEntries(sections.map(section => [section.id, section])),
  'choose-stop': jump, 'previous-stop': prev, 'next-stop': next,
  'stop-progress': progress};
const doc = {
  querySelectorAll(selector) {
    if (selector === '.reader-nav a') return links;
    if (selector === '.history-chapters a[href^="#"]') return sectionLinks;
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
assert.equal(jump.value, 'plaza');
assert.equal(prev.disabled, true);
assert.equal(next.disabled, false);
jump.listener(); // Safari no hashchange when reselecting current stop.
assert.equal(stops[0].heading.focused, 1, 'Same-stop activation must restore focus');
assert.equal(stops[0].scrolled, 2, 'Same-stop activation must scroll to the active stop');
jump.value = 'twin-stairs';
jump.listener();
assert.equal(location.hash, '#twin-stairs');
assert.equal(progress.textContent, 'Stop 2 of 3');
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
const planLink = links.find(link => link.hash === '#plan');
planLink.click();
location.hash = '#plan';
assert.equal(panels.plan.heading.focused, 1, 'Choosing Plan should focus its heading');
assert.equal(panels.explore.hidden, true);
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
// A reload in the same tab should restore the selected on-site stop without
// touching the annotation system's independent localStorage.
const key = 'cdmx:templo-mayor:explore-stop';
assert.equal(store.get(key), 'plaza');
store.set(key, 'older-stairs');
location._hash = '#explore';
vm.runInNewContext(code, {...sandbox}); // A fresh JS context simulates reload.
assert.equal(jump.value, 'older-stairs', 'Explore reload must resume a stored stop');
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
console.log('PASS: Discover TOC, Safari focus, pager, stop resume on reload, explicit deep links, and storage-blocked navigation');
