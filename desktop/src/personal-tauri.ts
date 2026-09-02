import { mountPersonal } from "./personal-renderer";
import { DesktopAdapter } from "./personal-adapter";
import type { PersonalApi } from "./personal-api";

const host = document.querySelector<HTMLDivElement>("#app");
declare const __PERSONAL_OPENAI__: boolean;
if (host) {
  const apiModule = __PERSONAL_OPENAI__
    ? import("./personal-api").then(({ personalApi }) => personalApi)
    : import("./personal-local-api").then(({ personalLocalApi }) => personalLocalApi);
  void apiModule.then((api) =>
    mountPersonal(new DesktopAdapter(api as unknown as PersonalApi), host),
  );
}
