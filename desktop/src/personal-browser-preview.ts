import "./personal-browser-preview.css";
import { createPersonalBrowserPreviewApi, type PreviewScenario } from "./personal-browser-preview-api";
import { mountPersonal } from "./personal-main";

const scenarioSelect = document.querySelector<HTMLSelectElement>("#preview-scenario");
const app = document.querySelector<HTMLDivElement>("#app");

if (!scenarioSelect || !app) throw new Error("Personal browser preview root is missing");

const selectedScenario = (): PreviewScenario => scenarioSelect.value as PreviewScenario;
const scrollToTop = () => {
  if (!window.navigator.userAgent.toLowerCase().includes("jsdom")) window.scrollTo(0, 0);
};
const mountScenario = () => {
  scrollToTop();
  app.replaceChildren();
  void mountPersonal(createPersonalBrowserPreviewApi(selectedScenario()), app);
};

scenarioSelect.addEventListener("change", mountScenario);
mountScenario();
