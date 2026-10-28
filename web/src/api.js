// The browser calls the same origin. Vite proxies /api in development.
// nginx proxies /api in the Compose `web` container. There is no CORS header
// on the API, and this page does not add one.

import { kpRequestPaths } from "./kp.js";

export async function loadKp(nowMs) {
  const paths = kpRequestPaths(nowMs);
  const [minute, threeHour] = await Promise.all([
    readPage(paths.minute),
    readPage(paths.threeHour),
  ]);
  return { minute, threeHour };
}

async function readPage(path) {
  try {
    return { ok: true, page: await getJson(path) };
  } catch (error) {
    return { ok: false, message: error.message };
  }
}

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${response.status} from ${path.split("?")[0]}`);
  }
  return response.json();
}
