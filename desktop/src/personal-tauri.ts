import { personalApi } from "./personal-api";
import { mountPersonal } from "./personal-main";

const host = document.querySelector<HTMLDivElement>("#app");
if (host) void mountPersonal(personalApi, host);
