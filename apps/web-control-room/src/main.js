import { loadRuntimeBundle } from "./runtimeBundle.js";
import { initializeDriveMode, renderApp } from "./renderApp.js?v=d13-live-seam-r2";

const app = document.querySelector("#app");

try {
  const bundle = await loadRuntimeBundle();
  app.innerHTML = renderApp(bundle);
  initializeDriveMode();
  document.body.dataset.sourceRecordStatus = bundle.productModes.bundle?.status || bundle.storyQueue.bundle?.status || bundle.storyFirst.bundle?.status || bundle.sourceRecords.bundle?.status || "missing";
  document.body.dataset.executionState = bundle.productModes.bundle?.execution_state || bundle.oneTruth.execution_state;
} catch (error) {
  app.innerHTML = `<section class="panel span-12"><h2>Runtime bundle load failed</h2><p>${error.message}</p></section>`;
}
