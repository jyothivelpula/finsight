export const DATA_CHANGED_EVENT = "finsight:data-changed";

export type DataChangedDetail = {
  kind: "income" | "expense" | "transaction";
};

export function emitDataChanged(detail: DataChangedDetail = { kind: "transaction" }) {
  window.dispatchEvent(new CustomEvent(DATA_CHANGED_EVENT, { detail }));
}

export function onDataChanged(handler: (detail: DataChangedDetail) => void) {
  const listener = (event: Event) => {
    const custom = event as CustomEvent<DataChangedDetail>;
    handler(custom.detail ?? { kind: "transaction" });
  };
  window.addEventListener(DATA_CHANGED_EVENT, listener);
  return () => window.removeEventListener(DATA_CHANGED_EVENT, listener);
}
