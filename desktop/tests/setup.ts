import { afterEach, beforeEach } from "vitest";

beforeEach(() => {
  document.documentElement.lang = "en";
  document.title = "PSYCHE OS desktop test";
  document.body.innerHTML = '<div id="app"></div>';
});

afterEach(() => {
  document.body.innerHTML = "";
});
