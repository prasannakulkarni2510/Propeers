// On phones every .table is restyled as a stack of cards (index.css), where
// each cell shows its column name before the value. The column name comes
// from a data-label attribute; rather than hand-maintain it on every <td> in
// every table, copy it from the table's own <th> row whenever tables render.
function labelTable(table) {
  const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim());
  if (!heads.length) return;
  for (const row of table.querySelectorAll("tbody tr")) {
    [...row.children].forEach((cell, i) => {
      const label = heads[i] || "";
      if (cell.getAttribute("data-label") !== label) cell.setAttribute("data-label", label);
    });
  }
}

export function startTableLabels(root = document.body) {
  const run = () => root.querySelectorAll("table.table").forEach(labelTable);
  run();
  let queued = false;
  const observer = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      run();
    });
  });
  observer.observe(root, { childList: true, subtree: true });
  return () => observer.disconnect();
}
