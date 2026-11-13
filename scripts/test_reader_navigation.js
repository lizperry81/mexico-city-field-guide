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
const links = Object.keys(panels).map(id => ({
  hash: '#' + id, current: false,
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
  'choose-stop': jump, 'previous-stop': prev, 'next-stop': next,
  'stop-progress': progress};
const doc = {
  querySelectorAll(selector) {
    if (selector === '.reader-nav a') return links;
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
vm.runInNewContext(code, {
  document: doc, window: {addEventListener(type, fn) {listeners[type] = fn;}},
  location, Option: function(label, value) {return {label, value};},
  requestAnimationFrame(fn) {fn();}, HTMLDetailsElement: class {}
});
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
location.hash = '#plaza'; // Restore an Explore deep link.
assert.equal(panels.explore.hidden, false);
assert.equal(jump.value, 'plaza');
assert.equal(progress.textContent, 'Stop 1 of 3');
console.log('PASS: same-anchor Safari navigation, focus, pager and browser-history transitions');
