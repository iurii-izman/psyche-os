import "./personal-browser-preview.css";
import { createPersonalBrowserPreviewApi, type PreviewScenario } from "./personal-browser-preview-api";
import { PreviewAdapter } from "./personal-adapter";
import { mountPersonal } from "./personal-renderer";

const scenarioSelect = document.querySelector<HTMLSelectElement>("#preview-scenario");
const app = document.querySelector<HTMLDivElement>("#app");

if (!scenarioSelect || !app) throw new Error("Personal browser preview root is missing");

const selectedScenario = (): PreviewScenario => scenarioSelect.value as PreviewScenario;
const mountScenario = () => {
  app.replaceChildren();
  void mountPersonal(new PreviewAdapter(createPersonalBrowserPreviewApi(selectedScenario())), app);
};

scenarioSelect.addEventListener("change", mountScenario);
mountScenario();
